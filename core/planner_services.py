"""Django 与纯 Python planner/sim 之间的适配层。"""

from __future__ import annotations

from math import isfinite

from planner.registry import plan as run_plan
from planner.registry import replan as run_replan

from .models import SimulationRun, TaskPoint, UAV


PIXEL_TO_VIRTUAL_M = 0.1


def _scale_xy(item, scale):
    value = dict(item or {})
    if 'x' in value:
        value['x'] = float(value['x']) * scale
    elif 'coordinate_x' in value:
        value['coordinate_x'] = float(value['coordinate_x']) * scale
    if 'y' in value:
        value['y'] = float(value['y']) * scale
    elif 'coordinate_y' in value:
        value['coordinate_y'] = float(value['coordinate_y']) * scale
    return value


def _scale_tasks(tasks, scale):
    return [_scale_xy(item, scale) for item in tasks or []]


def _scale_uavs(uavs, scale):
    result = []
    for item in uavs or []:
        value = _scale_xy(item, scale)
        if 'position_x' in value and 'x' not in value:
            value['position_x'] = float(value['position_x']) * scale
        if 'position_y' in value and 'y' not in value:
            value['position_y'] = float(value['position_y']) * scale
        home = value.get('home')
        if isinstance(home, dict):
            value['home'] = _scale_xy(home, scale)
        else:
            for axis in ('home_x', 'home_y'):
                if value.get(axis) is not None:
                    value[axis] = float(value[axis]) * scale
        result.append(value)
    return result


def _scale_map_state(map_state, scale):
    value = dict(map_state or {})
    if 'width' in value:
        value['width'] = float(value['width']) * scale
    if 'height' in value:
        value['height'] = float(value['height']) * scale
    if isinstance(value.get('home'), dict):
        value['home'] = _scale_xy(value['home'], scale)
    for key in ('obstacles', 'no_fly_zones', 'restricted_zones'):
        polygons = []
        for polygon in value.get(key) or []:
            polygons.append([_scale_xy(point, scale) if isinstance(point, dict) else [point[0] * scale, point[1] * scale] for point in polygon])
        if key in value:
            value[key] = polygons
    return value


def _scale_route(route, scale):
    value = dict(route or {})
    for key in ('start', 'return'):
        if isinstance(value.get(key), dict):
            value[key] = _scale_xy(value[key], scale)
    value['tasks'] = [_scale_xy(item, scale) for item in value.get('tasks') or []]
    return value


def _scale_routes(routes, scale):
    return {str(uav_id): _scale_route(route, scale) for uav_id, route in (routes or {}).items()}


def _restore_result(result, scale):
    if scale == 1:
        return result
    result.routes = _scale_routes(result.routes, 1.0 / scale)
    result.config = dict(result.config or {})
    result.config.update({
        'coordinate_scale': scale,
        'coordinate_units': 'virtual_m',
        'display_units': 'image_px',
    })
    result.metrics = dict(result.metrics or {})
    result.metrics['coordinate_scale'] = scale
    return result


def _coordinate_scale(payload):
    config = payload.get('config') or {}
    raw = payload.get('coordinate_scale', config.get('coordinate_scale', 1.0))
    try:
        scale = float(raw)
    except (TypeError, ValueError):
        scale = 1.0
    if scale <= 0:
        raise ValueError('coordinate_scale 必须大于 0。')
    return scale


def _scale_event(event, scale):
    value = dict(event or {})
    if isinstance(value.get('task'), dict):
        value['task'] = _scale_xy(value['task'], scale)
    return value


def _default_uavs(map_state):
    state = dict(map_state or {})
    width = float(state.get('width') or 100)
    height = float(state.get('height') or 100)
    home_x = width * 0.5
    home_y = height * 0.92
    return [
        {'id': 'UAV-01', 'x': home_x - width * 0.08, 'y': home_y, 'home': {'x': home_x, 'y': home_y}, 'battery_level': 82, 'status': 'idle'},
        {'id': 'UAV-02', 'x': home_x, 'y': home_y, 'home': {'x': home_x, 'y': home_y}, 'battery_level': 64, 'status': 'idle'},
        {'id': 'UAV-03', 'x': home_x + width * 0.08, 'y': home_y, 'home': {'x': home_x, 'y': home_y}, 'battery_level': 91, 'status': 'idle'},
    ]


def mission_tasks(mission_id):
    return [
        {
            'id': str(item.pk),
            'x': item.coordinate_x,
            'y': item.coordinate_y,
            'category': item.disaster_category,
            'area': item.area,
            'confidence': item.confidence,
            'uncertainty': 1.0 - item.confidence,
            'priority': item.priority,
            'status': item.status,
        }
        for item in TaskPoint.objects.filter(mission_id=mission_id).order_by('-priority', 'id')
    ]


def all_uavs():
    return [
        {
            'id': item.identifier,
            'x': item.position_x,
            'y': item.position_y,
            'battery_level': item.battery_level,
            'payload_capacity': item.payload_capacity,
            'status': item.status,
        }
        for item in UAV.objects.all().order_by('identifier')
    ]


def preview(payload, mission_id=None):
    tasks = payload.get('tasks') or (mission_tasks(mission_id) if mission_id else [])
    map_state = payload.get('map_state') or {}
    uavs = payload.get('uavs') or payload.get('uav_configuration') or all_uavs() or _default_uavs(map_state)
    if not tasks:
        raise ValueError('没有可调度任务，请先生成任务点或传入 tasks。')
    scale = _coordinate_scale(payload)
    config = dict(payload.get('config') or {})
    config.update({key: payload[key] for key in ('algorithm', 'planning_method', 'random_seed') if key in payload})
    config['algorithm'] = config.get('algorithm') or config.get('planning_method') or 'risk_aware_pso'
    result = run_plan(
        _scale_tasks(tasks, scale),
        _scale_uavs(uavs, scale),
        _scale_map_state(map_state, scale),
        config,
    )
    return _restore_result(result, scale)


def _snapshot_id(value, field):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise ValueError(f'{field} 必须是有效的编号。')
    return str(value)


def _snapshot_number(value, field, maximum=None):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f'{field} 必须是有限的非负数。') from None
    if isinstance(value, bool) or not isfinite(number) or number < 0:
        raise ValueError(f'{field} 必须是有限的非负数。')
    if maximum is not None and number > maximum:
        raise ValueError(f'{field} 超出允许范围。')
    return number


def simulation_snapshot(run):
    summary = run.summary_metrics or {}
    return {
        'tasks': [dict(item) for item in run.task_snapshot or []],
        'uavs': [dict(item) for item in run.uav_configuration or []],
        'map_state': summary.get('map_state') or {},
        'routes': summary.get('routes') or {},
    }


def merge_current_state(state, current_state):
    """把客户端可更新的飞行状态合并到服务端的仿真快照。"""
    if not isinstance(current_state, dict):
        raise ValueError('current_state 必须是对象。')
    telemetry = current_state.get('uavs', [])
    completed_ids = current_state.get('completed_task_ids', [])
    if not isinstance(telemetry, list) or not isinstance(completed_ids, list):
        raise ValueError('current_state.uavs 和 completed_task_ids 必须是数组。')
    known_uavs = {str(item.get('id', item.get('identifier'))): item for item in state['uavs']}
    known_tasks = {str(item.get('id', item.get('task_id'))): item for item in state['tasks']}
    bounds = state['map_state']
    seen = set()
    for item in telemetry:
        if not isinstance(item, dict):
            raise ValueError('current_state.uavs 每项必须是对象。')
        uav_id = _snapshot_id(item.get('id'), 'current_state.uavs.id')
        if uav_id not in known_uavs or uav_id in seen:
            raise ValueError(f'当前仿真的无人机编号不存在或重复：{uav_id}。')
        seen.add(uav_id)
        uav = known_uavs[uav_id]
        for axis, dimension in (('x', 'width'), ('y', 'height')):
            limit = bounds.get(dimension)
            limit = _snapshot_number(limit, dimension) if limit is not None else None
            uav[axis] = _snapshot_number(item.get(axis), f'{uav_id}.{axis}', limit)
            # 旧运行可能用 position_x/y 保存坐标，更新时同步其别名。
            if f'position_{axis}' in uav:
                uav[f'position_{axis}'] = uav[axis]
        battery = _snapshot_number(item.get('battery_level'), f'{uav_id}.battery_level', 100)
        previous_battery = uav.get('battery_level', uav.get('battery'))
        if previous_battery is not None and battery > float(previous_battery) + 1e-6:
            raise ValueError(f'{uav_id} 的电量不能高于已保存的飞行状态。')
        uav['battery_level'] = battery
    for raw_id in completed_ids:
        task_id = _snapshot_id(raw_id, 'completed_task_ids')
        if task_id not in known_tasks:
            raise ValueError(f'当前仿真的任务编号不存在：{task_id}。')
        if known_tasks[task_id].get('status') != 'cancelled':
            known_tasks[task_id]['status'] = 'completed'


def replan_simulation(simulation_run: SimulationRun, event_payload=None, config=None):
    event_payload = dict(event_payload or {})
    summary_before = simulation_run.summary_metrics or {}
    before = simulation_snapshot(simulation_run)
    if 'current_state' in event_payload:
        merge_current_state(before, event_payload['current_state'])

    updated_tasks = list(before['tasks'])
    events = list(simulation_run.events.values('event_type', 'uav_id', 'task_point_id', 'state_after'))
    if event_payload:
        events.append(event_payload)
        if event_payload.get('event_type') == 'task_added' and event_payload.get('task'):
            task = event_payload['task']
            if not isinstance(task, dict):
                raise ValueError('新增任务必须是对象。')
            task_id = _snapshot_id(task.get('id', task.get('task_id')), 'task.id')
            if not any(str(item.get('id', item.get('task_id'))) == task_id for item in updated_tasks):
                updated_tasks.append(dict(task))
    pending = [item for item in updated_tasks if item.get('status') not in {'completed', 'cancelled'}]
    stored_config = summary_before.get('config') or (summary_before.get('planner') or {}).get('config') or {}
    cfg = dict(stored_config)
    cfg.update(config or {})
    cfg.setdefault('algorithm', 'risk_aware_pso')
    cfg.setdefault('random_seed', simulation_run.random_seed)
    try:
        scale = float(summary_before.get('coordinate_scale', 1.0) or 1.0)
    except (TypeError, ValueError):
        scale = 1.0
    if scale <= 0:
        scale = 1.0
    planner_state = dict(before)
    planner_state['tasks'] = _scale_tasks(updated_tasks, scale)
    planner_state['uavs'] = _scale_uavs(before['uavs'], scale)
    planner_state['map_state'] = _scale_map_state(before['map_state'], scale)
    planner_state['routes'] = _scale_routes(before['routes'], scale)
    planner_pending = _scale_tasks(pending, scale)
    planner_events = [_scale_event(item, scale) for item in events]
    result = run_replan(planner_state, planner_pending, planner_events, cfg)
    result = _restore_result(result, scale)
    summary = dict(simulation_run.summary_metrics or {})
    summary.update(result.to_dict())
    summary['map_state'] = before['map_state']
    summary['coordinate_scale'] = scale
    updated_uavs = [dict(item) for item in before['uavs']]
    if event_payload.get('uav_id') and event_payload.get('event_type') in {'uav_failure', 'failure', 'low_battery'}:
        for item in updated_uavs:
            if str(item.get('id', item.get('identifier'))) == str(event_payload['uav_id']):
                item['status'] = 'failed' if event_payload['event_type'] in {'uav_failure', 'failure'} else 'low_battery'
    simulation_run.uav_configuration = updated_uavs
    simulation_run.task_snapshot = updated_tasks
    simulation_run.summary_metrics = summary
    simulation_run.status = SimulationRun.Status.RUNNING
    simulation_run.save(update_fields=['uav_configuration', 'task_snapshot', 'summary_metrics', 'status', 'updated_at'])
    return result, before, summary

