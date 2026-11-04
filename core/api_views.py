"""供 Vue 前端使用的数据库 JSON API。

本模块只负责参数校验、模型持久化和 JSON 序列化，不包含模型训练、推理或调度算法。
"""

import json
import uuid
from functools import wraps
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from .models import (
    Dataset,
    ExperimentResult,
    Mission,
    ModelArtifact,
    SimulationEvent,
    SimulationRun,
    TaskPoint,
    UAV,
)


class APIInputError(Exception):
    """表示前端提交的数据缺失或格式不正确。"""

    def __init__(self, message, code='invalid_input', status=400):
        self.message = message
        self.code = code
        self.status = status
        super().__init__(message)


def _ok(data, status=200):
    """返回统一成功结构。"""
    return JsonResponse({'success': True, 'data': data, 'error': None}, status=status)


def _fail(message, code='invalid_input', status=400, details=None):
    """返回统一失败结构。"""
    error = {'code': code, 'message': message}
    if details:
        error['details'] = details
    return JsonResponse({'success': False, 'data': None, 'error': error}, status=status)


def api_errors(view_func):
    """把 JSON 解析、字段校验和数据库冲突转换成前端可读的错误。"""

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except APIInputError as exc:
            return _fail(exc.message, exc.code, exc.status)
        except ValidationError as exc:
            details = getattr(exc, 'message_dict', None) or {'fields': exc.messages}
            return _fail('提交的数据未通过模型校验。', 'model_validation_error', 400, details)
        except IntegrityError:
            return _fail('数据与已有记录冲突，请检查唯一字段或外键关系。', 'integrity_error', 409)

    return wrapped


def _payload(request):
    """解析 JSON 请求体，并要求顶层对象为字典。"""
    if not request.body:
        return {}
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise APIInputError('请求体必须是合法的 UTF-8 JSON。', 'invalid_json') from exc
    if not isinstance(payload, dict):
        raise APIInputError('请求体顶层必须是 JSON 对象。', 'invalid_json')
    return payload


def _required(payload, *names):
    """读取必填字段，允许 0 等有效值。"""
    values = []
    for name in names:
        value = payload.get(name)
        if value is None or value == '':
            raise APIInputError(f'缺少必填字段：{name}。', 'missing_field')
        values.append(value)
    return values[0] if len(values) == 1 else values


def _int_value(payload, name, default=0, minimum=None):
    """读取整数配置字段。"""
    value = payload.get(name, default)
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise APIInputError(f'字段 {name} 必须是整数。', 'invalid_field') from exc
    if minimum is not None and value < minimum:
        raise APIInputError(f'字段 {name} 不能小于 {minimum}。', 'invalid_field')
    return value


def _float_value(payload, name, default=0.0, minimum=None, maximum=None):
    """读取浮点配置字段。"""
    value = payload.get(name, default)
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise APIInputError(f'字段 {name} 必须是数字。', 'invalid_field') from exc
    if minimum is not None and value < minimum:
        raise APIInputError(f'字段 {name} 不能小于 {minimum}。', 'invalid_field')
    if maximum is not None and value > maximum:
        raise APIInputError(f'字段 {name} 不能大于 {maximum}。', 'invalid_field')
    return value


def _related(model, value, field_name):
    """根据外键 ID 获取对象，并给出统一的 404 错误。"""
    try:
        return model.objects.get(pk=value)
    except (model.DoesNotExist, ValueError, TypeError) as exc:
        raise APIInputError(f'{field_name} 对应的记录不存在。', 'related_object_not_found', 404) from exc


def _page(request, queryset, serializer):
    """为列表接口提供简单的 limit/offset 分页。"""
    try:
        limit = min(max(int(request.GET.get('limit', 50)), 1), 100)
        offset = max(int(request.GET.get('offset', 0)), 0)
    except ValueError as exc:
        raise APIInputError('limit 和 offset 必须是整数。', 'invalid_pagination') from exc
    return {
        'items': [serializer(item) for item in queryset[offset:offset + limit]],
        'count': queryset.count(),
        'limit': limit,
        'offset': offset,
    }


def _iso(value):
    """把可空时间序列化为 ISO 8601 字符串。"""
    return value.isoformat() if value else None


def _dataset_data(item):
    return {
        'id': item.pk,
        'name': item.name,
        'source_url': item.source_url,
        'license_name': item.license_name,
        'version': item.version,
        'categories': item.categories,
        'local_index_path': item.local_index_path,
        'created_at': _iso(item.created_at),
        'updated_at': _iso(item.updated_at),
    }


def _model_artifact_data(item):
    return {
        'id': item.pk,
        'name': item.name,
        'algorithm_type': item.algorithm_type,
        'algorithm_type_label': item.get_algorithm_type_display(),
        'weight_path': item.weight_path,
        'training_config': item.training_config,
        'data_version': item.data_version,
        'evaluation_metrics': item.evaluation_metrics,
        'dataset_id': item.dataset_id,
        'created_at': _iso(item.created_at),
        'updated_at': _iso(item.updated_at),
    }


def _mission_data(item):
    return {
        'id': item.pk,
        'name': item.name,
        'input_image_path': item.input_image_path,
        'mask_path': item.mask_path,
        'status': item.status,
        'status_label': item.get_status_display(),
        'model_artifact_id': item.model_artifact_id,
        'created_at': _iso(item.created_at),
        'updated_at': _iso(item.updated_at),
    }


def _uav_data(item):
    return {
        'id': item.pk,
        'identifier': item.identifier,
        'name': item.name,
        'position_x': item.position_x,
        'position_y': item.position_y,
        'battery_level': item.battery_level,
        'payload_capacity': item.payload_capacity,
        'status': item.status,
        'status_label': item.get_status_display(),
        'created_at': _iso(item.created_at),
        'updated_at': _iso(item.updated_at),
    }


def _task_point_data(item):
    return {
        'id': item.pk,
        'mission_id': item.mission_id,
        'coordinate_x': item.coordinate_x,
        'coordinate_y': item.coordinate_y,
        'disaster_category': item.disaster_category,
        'disaster_category_label': item.get_disaster_category_display(),
        'area': item.area,
        'confidence': item.confidence,
        'priority': item.priority,
        'status': item.status,
        'status_label': item.get_status_display(),
        'assigned_uav_id': item.assigned_uav_id,
        'created_at': _iso(item.created_at),
        'updated_at': _iso(item.updated_at),
    }


def _simulation_run_data(item):
    return {
        'id': item.pk,
        'mission_id': item.mission_id,
        'planning_method': item.planning_method,
        'planning_method_label': item.get_planning_method_display(),
        'random_seed': item.random_seed,
        'uav_configuration': item.uav_configuration,
        'task_snapshot': item.task_snapshot,
        'summary_metrics': item.summary_metrics,
        'status': item.status,
        'status_label': item.get_status_display(),
        'started_at': _iso(item.started_at),
        'finished_at': _iso(item.finished_at),
        'created_at': _iso(item.created_at),
        'updated_at': _iso(item.updated_at),
    }


def _simulation_event_data(item):
    return {
        'id': item.pk,
        'simulation_run_id': item.simulation_run_id,
        'event_type': item.event_type,
        'event_type_label': item.get_event_type_display(),
        'uav_id': item.uav_id,
        'task_point_id': item.task_point_id,
        'state_before': item.state_before,
        'state_after': item.state_after,
        'occurred_at': _iso(item.occurred_at),
    }


def _experiment_result_data(item):
    return {
        'id': item.pk,
        'simulation_run_id': item.simulation_run_id,
        'baseline_method': item.baseline_method,
        'baseline_method_label': item.get_baseline_method_display(),
        'experiment_parameters': item.experiment_parameters,
        'metrics': item.metrics,
        'log_path': item.log_path,
        'result_file_path': item.result_file_path,
        'created_at': _iso(item.created_at),
        'updated_at': _iso(item.updated_at),
    }


@require_GET
@ensure_csrf_cookie
def csrf_token(request):
    """为 Vue 前端设置 CSRF Cookie，并返回 token 供请求头使用。"""
    return _ok({'csrf_token': get_token(request)})


@require_GET
def health(request):
    """返回 API 和数据库服务状态。"""
    return _ok({'service': 'core-api', 'status': 'ok', 'database': 'ok'})


@api_errors
@require_http_methods(['POST'])
def vision_infer(request):
    """上传一张航拍图并调用已训练的 FloodNet 分割模型。"""
    uploaded = request.FILES.get('image')
    if uploaded is None:
        raise APIInputError('请使用 multipart/form-data 上传 image 文件。', 'missing_image')
    if not (uploaded.content_type or '').startswith('image/'):
        raise APIInputError('只支持 JPG、PNG 等图像文件。', 'invalid_image_type')
    if uploaded.size > 20 * 1024 * 1024:
        raise APIInputError('图像不能超过 20 MB。', 'image_too_large')

    artifact = None
    if request.POST.get('model_artifact_id'):
        artifact = _related(ModelArtifact, request.POST['model_artifact_id'], 'model_artifact_id')
    else:
        # 未指定模型时使用最近登记的深度分割制品，并保留环境变量默认权重作为兜底。
        artifact = ModelArtifact.objects.filter(
            algorithm_type=ModelArtifact.AlgorithmType.DEEP_SEGMENTATION,
        ).order_by('-created_at').first()
    try:
        from vision.infer import ModelUnavailable, get_engine
        engine = get_engine(artifact.weight_path if artifact else None)
        result = engine.predict(uploaded)
    except (ModelUnavailable, ImportError) as exc:
        return _fail(str(exc), 'model_unavailable', 503)
    except (OSError, ValueError) as exc:
        return _fail(f'图像处理失败：{exc}', 'inference_failed', 422)

    suffix = Path(uploaded.name).suffix.lower() or '.jpg'
    token = uuid.uuid4().hex
    uploaded.seek(0)
    image_rel = default_storage.save(f'missions/{token}{suffix}', ContentFile(uploaded.read()))
    mask_rel = default_storage.save(f'missions/{token}_mask.png', ContentFile(result.pop('mask_bytes')))
    mission_name = request.POST.get('name') or Path(uploaded.name).stem
    mission = Mission(
        name=mission_name[:150],
        input_image_path=image_rel,
        mask_path=mask_rel,
        status=Mission.Status.READY,
        model_artifact=artifact,
    )
    mission.full_clean()
    mission.save()

    result.update({
        'mission_id': mission.pk,
        'input_image_path': image_rel,
        'input_image_url': default_storage.url(image_rel),
        'mask_path': mask_rel,
        'mask_url': default_storage.url(mask_rel),
        'model_artifact_id': artifact.pk if artifact else None,
    })
    return _ok(result, status=201)


@api_errors
@require_http_methods(['GET', 'POST'])
def datasets(request):
    """查询或新增数据集记录。"""
    if request.method == 'GET':
        queryset = Dataset.objects.all()
        return _ok(_page(request, queryset, _dataset_data))
    payload = _payload(request)
    name, source_url, license_name, version, local_index_path = _required(
        payload, 'name', 'source_url', 'license_name', 'version', 'local_index_path'
    )
    item = Dataset(
        name=name,
        source_url=source_url,
        license_name=license_name,
        version=version,
        categories=payload.get('categories', []),
        local_index_path=local_index_path,
    )
    item.full_clean()
    item.save()
    return _ok(_dataset_data(item), status=201)


@api_errors
@require_http_methods(['GET', 'POST'])
def model_artifacts(request):
    """查询或新增模型制品记录。"""
    if request.method == 'GET':
        queryset = ModelArtifact.objects.select_related('dataset').all()
        return _ok(_page(request, queryset, _model_artifact_data))
    payload = _payload(request)
    name, algorithm_type, weight_path, data_version, dataset_id = _required(
        payload, 'name', 'algorithm_type', 'weight_path', 'data_version', 'dataset_id'
    )
    item = ModelArtifact(
        name=name,
        algorithm_type=algorithm_type,
        weight_path=weight_path,
        training_config=payload.get('training_config', {}),
        data_version=data_version,
        evaluation_metrics=payload.get('evaluation_metrics', {}),
        dataset=_related(Dataset, dataset_id, 'dataset_id'),
    )
    item.full_clean()
    item.save()
    return _ok(_model_artifact_data(item), status=201)


@api_errors
@require_http_methods(['GET', 'POST'])
def missions(request):
    """查询或新增灾情复查任务记录。"""
    if request.method == 'GET':
        queryset = Mission.objects.select_related('model_artifact').all()
        return _ok(_page(request, queryset, _mission_data))
    payload = _payload(request)
    name, input_image_path = _required(payload, 'name', 'input_image_path')
    model_artifact = None
    if payload.get('model_artifact_id') is not None:
        model_artifact = _related(ModelArtifact, payload['model_artifact_id'], 'model_artifact_id')
    item = Mission(
        name=name,
        input_image_path=input_image_path,
        mask_path=payload.get('mask_path', ''),
        status=payload.get('status', Mission.Status.CREATED),
        model_artifact=model_artifact,
    )
    item.full_clean()
    item.save()
    return _ok(_mission_data(item), status=201)


@api_errors
@require_http_methods(['GET', 'POST'])
def task_points(request):
    """查询或新增复查任务点记录。"""
    if request.method == 'GET':
        queryset = TaskPoint.objects.select_related('mission', 'assigned_uav').all()
        if request.GET.get('mission_id'):
            queryset = queryset.filter(mission_id=request.GET['mission_id'])
        return _ok(_page(request, queryset, _task_point_data))
    payload = _payload(request)
    mission_id, category = _required(payload, 'mission_id', 'disaster_category')
    mission = _related(Mission, mission_id, 'mission_id')
    assigned_uav = None
    if payload.get('assigned_uav_id') is not None:
        assigned_uav = _related(UAV, payload['assigned_uav_id'], 'assigned_uav_id')
    item = TaskPoint(
        mission=mission,
        coordinate_x=_float_value(payload, 'coordinate_x', payload.get('x', 0), minimum=0),
        coordinate_y=_float_value(payload, 'coordinate_y', payload.get('y', 0), minimum=0),
        disaster_category=category,
        area=_float_value(payload, 'area', 0, minimum=0),
        confidence=_float_value(payload, 'confidence', 0, minimum=0, maximum=1),
        priority=_int_value(payload, 'priority', 0, minimum=0),
        status=payload.get('status', TaskPoint.Status.PENDING),
        assigned_uav=assigned_uav,
    )
    item.full_clean()
    item.save()
    return _ok(_task_point_data(item), status=201)


@api_errors
@require_http_methods(['GET', 'POST'])
def uavs(request):
    """查询或新增虚拟无人机记录。"""
    if request.method == 'GET':
        queryset = UAV.objects.all()
        return _ok(_page(request, queryset, _uav_data))
    payload = _payload(request)
    identifier = _required(payload, 'identifier')
    item = UAV(
        identifier=identifier,
        name=payload.get('name', ''),
        position_x=_float_value(payload, 'position_x', payload.get('x', 0), minimum=0),
        position_y=_float_value(payload, 'position_y', payload.get('y', 0), minimum=0),
        battery_level=_float_value(payload, 'battery_level', payload.get('battery', 100), minimum=0, maximum=100),
        payload_capacity=_float_value(payload, 'payload_capacity', 0, minimum=0),
        status=payload.get('status', UAV.Status.IDLE),
    )
    item.full_clean()
    item.save()
    return _ok(_uav_data(item), status=201)


@api_errors
@require_http_methods(['GET', 'POST'])
def simulation_runs(request):
    """查询或新增调度仿真运行记录。"""
    if request.method == 'GET':
        queryset = SimulationRun.objects.select_related('mission').all()
        if request.GET.get('mission_id'):
            queryset = queryset.filter(mission_id=request.GET['mission_id'])
        return _ok(_page(request, queryset, _simulation_run_data))
    payload = _payload(request)
    mission_id, planning_method = _required(payload, 'mission_id', 'planning_method')
    item = SimulationRun(
        mission=_related(Mission, mission_id, 'mission_id'),
        planning_method=planning_method,
        random_seed=_int_value(payload, 'random_seed', 42, minimum=0),
        uav_configuration=payload.get('uav_configuration', []),
        task_snapshot=payload.get('task_snapshot', []),
        summary_metrics=payload.get('summary_metrics', {}),
        status=payload.get('status', SimulationRun.Status.CREATED),
    )
    item.full_clean()
    item.save()
    return _ok(_simulation_run_data(item), status=201)


@api_errors
@require_http_methods(['GET', 'POST'])
def simulation_events(request, simulation_id):
    """查询或新增某次仿真的事件记录。"""
    simulation_run = _related(SimulationRun, simulation_id, 'simulation_id')
    if request.method == 'GET':
        queryset = simulation_run.events.select_related('uav', 'task_point').all()
        return _ok(_page(request, queryset, _simulation_event_data))
    payload = _payload(request)
    event_type = _required(payload, 'event_type')
    uav = _related(UAV, payload['uav_id'], 'uav_id') if payload.get('uav_id') is not None else None
    task_point = _related(TaskPoint, payload['task_point_id'], 'task_point_id') if payload.get('task_point_id') is not None else None
    item = SimulationEvent(
        simulation_run=simulation_run,
        event_type=event_type,
        uav=uav,
        task_point=task_point,
        state_before=payload.get('state_before', {}),
        state_after=payload.get('state_after', {}),
    )
    item.full_clean()
    item.save()
    return _ok(_simulation_event_data(item), status=201)


@api_errors
@require_GET
def all_simulation_events(request):
    """查询全部仿真事件，支持按仿真运行 ID 筛选。"""
    queryset = SimulationEvent.objects.select_related('simulation_run', 'uav', 'task_point').all()
    if request.GET.get('simulation_id'):
        queryset = queryset.filter(simulation_run_id=request.GET['simulation_id'])
    return _ok(_page(request, queryset, _simulation_event_data))


@api_errors
@require_http_methods(['GET', 'POST'])
def experiment_results(request):
    """查询或新增实验结果记录。"""
    if request.method == 'GET':
        queryset = ExperimentResult.objects.select_related('simulation_run').all()
        return _ok(_page(request, queryset, _experiment_result_data))
    payload = _payload(request)
    simulation_id, baseline_method = _required(payload, 'simulation_id', 'baseline_method')
    item = ExperimentResult(
        simulation_run=_related(SimulationRun, simulation_id, 'simulation_id'),
        baseline_method=baseline_method,
        experiment_parameters=payload.get('experiment_parameters', {}),
        metrics=payload.get('metrics', {}),
        log_path=payload.get('log_path', ''),
        result_file_path=payload.get('result_file_path', ''),
    )
    item.full_clean()
    item.save()
    return _ok(_experiment_result_data(item), status=201)

