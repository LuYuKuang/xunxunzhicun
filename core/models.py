"""汛巡智群核心业务模型。

本文件只负责数据结构、约束和持久化关系，不包含视图、接口或算法实现。
"""

import re

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def validate_relative_path(value):
    """校验文件字段只能保存相对路径，避免把本机绝对路径写入数据库。"""
    if not value:
        return
    normalized = str(value).replace('\\', '/')
    if normalized.startswith('/') or re.match(r'^[A-Za-z]:/', normalized):
        raise ValidationError('文件路径必须是相对路径，不能使用本机绝对路径。')
    if any(part == '..' for part in normalized.split('/')):
        raise ValidationError('文件路径不能包含 .. 路径穿越片段。')


class PlanningMethod(models.TextChoices):
    """调度算法枚举，供仿真运行和实验结果复用。"""

    ROUND_ROBIN = 'round_robin', '平均分配'
    NEAREST = 'nearest', '最近任务优先'
    PSO = 'pso', '标准离散 PSO'
    RISK_AWARE_PSO = 'risk_aware_pso', '风险加权 PSO'


class Dataset(models.Model):
    """数据集登记信息，记录来源、许可和本地索引位置。"""

    name = models.CharField(
        '数据集名称',
        max_length=150,
        db_index=True,
        help_text='数据集的显示名称，例如 FloodNet。',
    )
    source_url = models.URLField(
        '来源 URL',
        max_length=500,
        help_text='数据集的公开来源地址或官方发布地址。',
    )
    license_name = models.CharField(
        '许可证',
        max_length=150,
        help_text='数据集使用的许可证名称。',
    )
    version = models.CharField(
        '数据集版本',
        max_length=80,
        db_index=True,
        help_text='数据集版本、快照日期或发布编号。',
    )
    categories = models.JSONField(
        '类别列表',
        default=list,
        blank=True,
        help_text='数据集类别名称列表，例如受淹道路、受淹建筑和水体。',
    )
    local_index_path = models.CharField(
        '本地索引路径',
        max_length=500,
        validators=[validate_relative_path],
        help_text='图像或标注索引文件的相对路径，不保存图像二进制。',
    )
    created_at = models.DateTimeField(
        '创建时间',
        auto_now_add=True,
        db_index=True,
        help_text='数据集记录首次创建的时间。',
    )
    updated_at = models.DateTimeField(
        '更新时间',
        auto_now=True,
        help_text='数据集记录最近一次修改的时间。',
    )

    class Meta:
        verbose_name = '数据集'
        verbose_name_plural = '数据集'
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(fields=('name', 'version'), name='uniq_dataset_name_version'),
        ]

    def __str__(self):
        return f'{self.name} ({self.version})'


class ModelArtifact(models.Model):
    """模型制品信息，记录权重、训练配置、数据版本和评估结果。"""

    class AlgorithmType(models.TextChoices):
        """模型算法类型枚举。"""

        DEEP_SEGMENTATION = 'deep_segmentation', '深度学习分割'
        DEEP_CLASSIFICATION = 'deep_classification', '深度学习分类'
        CLASSICAL_SVM = 'classical_svm', '传统 SVM'
        CLASSICAL_RF = 'classical_rf', '随机森林'

    name = models.CharField(
        '模型名称',
        max_length=150,
        db_index=True,
        help_text='模型制品的显示名称，例如 FloodNet-Seg v1.2。',
    )
    algorithm_type = models.CharField(
        '算法类型',
        max_length=40,
        choices=AlgorithmType.choices,
        db_index=True,
        help_text='模型采用的深度学习或传统机器学习算法类型。',
    )
    weight_path = models.CharField(
        '权重相对路径',
        max_length=500,
        validators=[validate_relative_path],
        help_text='模型权重的相对路径，例如 vision/weights/floodnet.pth。',
    )
    training_config = models.JSONField(
        '训练配置',
        default=dict,
        blank=True,
        help_text='训练输入尺寸、增强、轮次、设备和超参数等配置。',
    )
    data_version = models.CharField(
        '数据版本',
        max_length=100,
        db_index=True,
        help_text='训练模型所使用的数据集版本或数据快照标识。',
    )
    evaluation_metrics = models.JSONField(
        '评估指标',
        default=dict,
        blank=True,
        help_text='mIoU、Dice、F1、召回率、推理耗时等评估结果。',
    )
    dataset = models.ForeignKey(
        Dataset,
        verbose_name='关联数据集',
        related_name='model_artifacts',
        on_delete=models.PROTECT,
        help_text='模型训练所使用的数据集，删除数据集前必须先处理模型制品。',
    )
    created_at = models.DateTimeField(
        '创建时间',
        auto_now_add=True,
        db_index=True,
        help_text='模型制品记录首次创建的时间。',
    )
    updated_at = models.DateTimeField(
        '更新时间',
        auto_now=True,
        help_text='模型制品记录最近一次修改的时间。',
    )

    class Meta:
        verbose_name = '模型制品'
        verbose_name_plural = '模型制品'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('algorithm_type', 'data_version'), name='model_algo_data_idx'),
        ]

    def __str__(self):
        return self.name


class Mission(models.Model):
    """一次灾情复查任务，保存输入图像、识别结果和任务状态。"""

    class Status(models.TextChoices):
        """任务生命周期状态枚举。"""

        CREATED = 'created', '已创建'
        INFERENCING = 'inferencing', '识别中'
        READY = 'ready', '待调度'
        PLANNING = 'planning', '规划中'
        RUNNING = 'running', '执行中'
        COMPLETED = 'completed', '已完成'
        FAILED = 'failed', '失败'

    name = models.CharField(
        '任务名称',
        max_length=150,
        db_index=True,
        help_text='一次灾情复查任务的名称。',
    )
    input_image_path = models.CharField(
        '输入图像相对路径',
        max_length=500,
        validators=[validate_relative_path],
        help_text='上传航拍图像在 media 或数据目录中的相对路径。',
    )
    mask_path = models.CharField(
        '识别 mask 相对路径',
        max_length=500,
        blank=True,
        validators=[validate_relative_path],
        help_text='模型生成的语义分割 mask 相对路径，可以为空。',
    )
    image_width = models.PositiveIntegerField(
        '输入图像宽度',
        null=True,
        blank=True,
        help_text='最近一次识别输入图像的像素宽度。',
    )
    image_height = models.PositiveIntegerField(
        '输入图像高度',
        null=True,
        blank=True,
        help_text='最近一次识别输入图像的像素高度。',
    )
    inference_summary = models.JSONField(
        '识别摘要',
        default=dict,
        blank=True,
        help_text='保存类别统计、平均置信度和推理元数据，供区域提取接口复用。',
    )
    status = models.CharField(
        '任务状态',
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
        help_text='任务当前所处的识别、调度或执行状态。',
    )
    model_artifact = models.ForeignKey(
        ModelArtifact,
        verbose_name='推理模型',
        related_name='missions',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='执行本次推理的模型制品，模型删除后保留任务记录。',
    )
    created_at = models.DateTimeField(
        '创建时间',
        auto_now_add=True,
        db_index=True,
        help_text='任务记录自动创建的时间。',
    )
    updated_at = models.DateTimeField(
        '更新时间',
        auto_now=True,
        help_text='任务记录最近一次修改的时间。',
    )

    class Meta:
        verbose_name = '灾情复查任务'
        verbose_name_plural = '灾情复查任务'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('status', 'created_at'), name='mission_status_created_idx'),
        ]

    def __str__(self):
        return self.name


class UAV(models.Model):
    """虚拟无人机实体，保存位置、电量、载荷和当前状态。"""

    class Status(models.TextChoices):
        """无人机状态枚举。"""

        IDLE = 'idle', '待命'
        ASSIGNED = 'assigned', '已分配'
        IN_FLIGHT = 'in_flight', '执行中'
        LOW_BATTERY = 'low_battery', '低电量'
        FAILED = 'failed', '故障退出'
        COMPLETED = 'completed', '已完成'
        OFFLINE = 'offline', '离线'

    identifier = models.CharField(
        '无人机编号',
        max_length=50,
        unique=True,
        help_text='虚拟无人机的唯一编号，例如 UAV-01。',
    )
    name = models.CharField(
        '无人机名称',
        max_length=100,
        blank=True,
        help_text='无人机的可读名称，例如侦察一号。',
    )
    position_x = models.FloatField(
        '当前位置 X',
        validators=[MinValueValidator(0.0)],
        help_text='二维仿真坐标中的 X 位置。',
    )
    position_y = models.FloatField(
        '当前位置 Y',
        validators=[MinValueValidator(0.0)],
        help_text='二维仿真坐标中的 Y 位置。',
    )
    battery_level = models.FloatField(
        '剩余电量百分比',
        default=100,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        db_index=True,
        help_text='当前剩余电量，取值范围为 0 到 100。',
    )
    payload_capacity = models.FloatField(
        '载荷能力',
        default=0,
        validators=[MinValueValidator(0.0)],
        help_text='虚拟无人机的载荷能力，单位由仿真配置定义。',
    )
    status = models.CharField(
        '当前状态',
        max_length=20,
        choices=Status.choices,
        default=Status.IDLE,
        db_index=True,
        help_text='无人机当前的待命、执行、低电量或故障状态。',
    )
    created_at = models.DateTimeField(
        '创建时间',
        auto_now_add=True,
        db_index=True,
        help_text='无人机记录自动创建的时间。',
    )
    updated_at = models.DateTimeField(
        '更新时间',
        auto_now=True,
        help_text='无人机记录最近一次修改的时间。',
    )

    class Meta:
        verbose_name = '虚拟无人机'
        verbose_name_plural = '虚拟无人机'
        ordering = ('identifier',)
        indexes = [
            models.Index(fields=('status', 'battery_level'), name='uav_status_battery_idx'),
        ]

    def __str__(self):
        return f'{self.identifier} - {self.name}' if self.name else self.identifier


class TaskPoint(models.Model):
    """由识别结果生成的复查任务点，关联所属 Mission 和可选执行无人机。"""

    class DisasterCategory(models.TextChoices):
        """灾情类别枚举。"""

        FLOODED_AREA = 'flooded_area', '受淹区域'
        FLOODED_ROAD = 'flooded_road', '受淹道路'
        FLOODED_BUILDING = 'flooded_building', '受淹建筑'
        WATER = 'water', '水体'

    class Status(models.TextChoices):
        """复查任务点状态枚举。"""

        PENDING = 'pending', '待复查'
        ASSIGNED = 'assigned', '已分配'
        IN_PROGRESS = 'in_progress', '执行中'
        COMPLETED = 'completed', '已完成'
        CANCELLED = 'cancelled', '已取消'

    mission = models.ForeignKey(
        Mission,
        verbose_name='所属复查任务',
        related_name='task_points',
        on_delete=models.CASCADE,
        help_text='任务点所属的灾情复查任务。',
    )
    coordinate_x = models.FloatField(
        '坐标 X',
        validators=[MinValueValidator(0.0)],
        help_text='二维仿真地图中的 X 坐标。',
    )
    coordinate_y = models.FloatField(
        '坐标 Y',
        validators=[MinValueValidator(0.0)],
        help_text='二维仿真地图中的 Y 坐标。',
    )
    disaster_category = models.CharField(
        '灾情类别',
        max_length=30,
        choices=DisasterCategory.choices,
        db_index=True,
        help_text='由模式识别模型输出的灾情类别。',
    )
    area = models.FloatField(
        '区域面积',
        validators=[MinValueValidator(0.0)],
        help_text='识别区域面积，单位由数据集或仿真配置定义。',
    )
    confidence = models.FloatField(
        '识别置信度',
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text='模型对该区域的置信度，取值范围为 0 到 1。',
    )
    priority = models.PositiveIntegerField(
        '复查优先级',
        default=0,
        db_index=True,
        help_text='由灾情等级、区域面积和识别不确定性计算的优先级。',
    )
    status = models.CharField(
        '任务点状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text='任务点当前的待复查、执行中或完成状态。',
    )
    assigned_uav = models.ForeignKey(
        UAV,
        verbose_name='执行无人机',
        related_name='assigned_task_points',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='当前负责该任务点的无人机，可在重规划时变更。',
    )
    created_at = models.DateTimeField(
        '创建时间',
        auto_now_add=True,
        db_index=True,
        help_text='任务点记录自动创建的时间。',
    )
    updated_at = models.DateTimeField(
        '更新时间',
        auto_now=True,
        help_text='任务点记录最近一次修改的时间。',
    )

    class Meta:
        verbose_name = '复查任务点'
        verbose_name_plural = '复查任务点'
        ordering = ('-priority', 'id')
        indexes = [
            models.Index(fields=('mission', 'status'), name='task_mission_status_idx'),
            models.Index(fields=('mission', 'priority'), name='task_mission_priority_idx'),
            models.Index(fields=('disaster_category', 'status'), name='task_category_status_idx'),
        ]

    def __str__(self):
        return f'{self.mission.name} - {self.get_disaster_category_display()} #{self.pk}'


class SimulationRun(models.Model):
    """一次多无人机调度仿真运行及其输入快照和汇总指标。"""

    class Status(models.TextChoices):
        """仿真运行状态枚举。"""

        CREATED = 'created', '已创建'
        RUNNING = 'running', '运行中'
        COMPLETED = 'completed', '已完成'
        FAILED = 'failed', '失败'
        CANCELLED = 'cancelled', '已取消'

    mission = models.ForeignKey(
        Mission,
        verbose_name='关联复查任务',
        related_name='simulation_runs',
        on_delete=models.PROTECT,
        help_text='本次仿真所使用的复查任务，保留任务后才能追溯实验。',
    )
    planning_method = models.CharField(
        '调度方法',
        max_length=30,
        choices=PlanningMethod.choices,
        db_index=True,
        help_text='本次仿真使用的任务分配和路径规划方法。',
    )
    random_seed = models.PositiveIntegerField(
        '随机种子',
        default=42,
        db_index=True,
        help_text='保证调度实验可复现的随机种子。',
    )
    uav_configuration = models.JSONField(
        '无人机配置快照',
        default=list,
        blank=True,
        help_text='仿真开始时的无人机位置、电量、容量和状态快照。',
    )
    task_snapshot = models.JSONField(
        '任务点快照',
        default=list,
        blank=True,
        help_text='仿真开始时的任务点坐标、优先级和状态快照。',
    )
    summary_metrics = models.JSONField(
        '汇总指标',
        default=dict,
        blank=True,
        help_text='总航程、完成时间、重点任务完成率、能耗和恢复率等指标。',
    )
    status = models.CharField(
        '仿真状态',
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
        help_text='本次仿真的生命周期状态。',
    )
    started_at = models.DateTimeField(
        '开始时间',
        null=True,
        blank=True,
        help_text='仿真实际开始执行的时间，由状态变为运行中时写入。',
    )
    finished_at = models.DateTimeField(
        '结束时间',
        null=True,
        blank=True,
        help_text='仿真结束、失败或取消的时间。',
    )
    created_at = models.DateTimeField(
        '创建时间',
        auto_now_add=True,
        db_index=True,
        help_text='仿真记录自动创建的时间。',
    )
    updated_at = models.DateTimeField(
        '更新时间',
        auto_now=True,
        help_text='仿真记录最近一次修改的时间。',
    )

    class Meta:
        verbose_name = '调度仿真运行'
        verbose_name_plural = '调度仿真运行'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('mission', 'status'), name='sim_mission_status_idx'),
            models.Index(fields=('planning_method', 'created_at'), name='sim_method_created_idx'),
        ]

    def __str__(self):
        return f'{self.mission.name} - {self.get_planning_method_display()} #{self.pk}'


class SimulationEvent(models.Model):
    """仿真过程中的故障、低电量、新任务和动态重规划事件。"""

    class EventType(models.TextChoices):
        """仿真事件类型枚举。"""

        UAV_FAILURE = 'uav_failure', '无人机故障'
        LOW_BATTERY = 'low_battery', '低电量'
        TASK_ADDED = 'task_added', '新增任务'
        REPLANNED = 'replanned', '动态重规划'

    simulation_run = models.ForeignKey(
        SimulationRun,
        verbose_name='所属仿真运行',
        related_name='events',
        on_delete=models.CASCADE,
        help_text='事件发生的仿真运行。',
    )
    event_type = models.CharField(
        '事件类型',
        max_length=20,
        choices=EventType.choices,
        db_index=True,
        help_text='故障、低电量、新增任务或动态重规划。',
    )
    uav = models.ForeignKey(
        UAV,
        verbose_name='相关无人机',
        related_name='simulation_events',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='事件涉及的无人机，可为空。',
    )
    task_point = models.ForeignKey(
        TaskPoint,
        verbose_name='相关任务点',
        related_name='simulation_events',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='事件涉及的任务点，可为空。',
    )
    state_before = models.JSONField(
        '事件前状态',
        default=dict,
        blank=True,
        help_text='事件发生前相关无人机、任务和路线的状态快照。',
    )
    state_after = models.JSONField(
        '事件后状态',
        default=dict,
        blank=True,
        help_text='事件处理后相关无人机、任务和路线的状态快照。',
    )
    occurred_at = models.DateTimeField(
        '发生时间',
        auto_now_add=True,
        db_index=True,
        help_text='事件记录自动创建的发生时间。',
    )

    class Meta:
        verbose_name = '仿真事件'
        verbose_name_plural = '仿真事件'
        ordering = ('-occurred_at',)
        indexes = [
            models.Index(fields=('simulation_run', 'occurred_at'), name='event_run_occurred_idx'),
            models.Index(fields=('event_type', 'occurred_at'), name='event_type_occurred_idx'),
        ]

    def __str__(self):
        return f'{self.simulation_run} - {self.get_event_type_display()} @ {self.occurred_at:%Y-%m-%d %H:%M:%S}'


class ExperimentResult(models.Model):
    """实验结果记录，保存基线方法、参数、指标和结果文件路径。"""

    simulation_run = models.ForeignKey(
        SimulationRun,
        verbose_name='关联仿真运行',
        related_name='experiment_results',
        on_delete=models.CASCADE,
        help_text='生成本实验结果的仿真运行。',
    )
    baseline_method = models.CharField(
        '基线方法',
        max_length=30,
        choices=PlanningMethod.choices,
        db_index=True,
        help_text='用于对比的平均分配、最近邻、标准 PSO 或风险加权 PSO。',
    )
    experiment_parameters = models.JSONField(
        '实验参数',
        default=dict,
        blank=True,
        help_text='任务数量、无人机数量、随机种子和约束配置等参数。',
    )
    metrics = models.JSONField(
        '实验指标',
        default=dict,
        blank=True,
        help_text='完成率、时间、航程、能耗、恢复率和重规划耗时等指标。',
    )
    log_path = models.CharField(
        '日志相对路径',
        max_length=500,
        blank=True,
        validators=[validate_relative_path],
        help_text='实验日志文件的相对路径，不保存日志二进制。',
    )
    result_file_path = models.CharField(
        '结果文件相对路径',
        max_length=500,
        blank=True,
        validators=[validate_relative_path],
        help_text='CSV、JSON 或图表结果文件的相对路径。',
    )
    created_at = models.DateTimeField(
        '创建时间',
        auto_now_add=True,
        db_index=True,
        help_text='实验结果记录自动创建的时间。',
    )
    updated_at = models.DateTimeField(
        '更新时间',
        auto_now=True,
        help_text='实验结果记录最近一次修改的时间。',
    )

    class Meta:
        verbose_name = '实验结果'
        verbose_name_plural = '实验结果'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('simulation_run', 'baseline_method'), name='result_run_method_idx'),
            models.Index(fields=('baseline_method', 'created_at'), name='result_method_created_idx'),
        ]

    def __str__(self):
        return f'{self.get_baseline_method_display()} - 仿真 #{self.simulation_run_id}'

