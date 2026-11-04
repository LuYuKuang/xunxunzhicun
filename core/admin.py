"""汛巡智群模型的 SimpleUI/Django Admin 注册配置。"""

from django.contrib import admin

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


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """数据集后台管理配置。"""

    list_display = ('name', 'version', 'license_name', 'local_index_path', 'created_at')
    search_fields = ('name', 'version', 'license_name', 'source_url')
    list_filter = ('license_name', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(ModelArtifact)
class ModelArtifactAdmin(admin.ModelAdmin):
    """模型制品后台管理配置。"""

    list_display = ('name', 'algorithm_type', 'dataset', 'data_version', 'weight_path', 'created_at')
    search_fields = ('name', 'data_version', 'weight_path', 'dataset__name')
    list_filter = ('algorithm_type', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('dataset',)
    ordering = ('-created_at',)


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    """灾情复查任务后台管理配置。"""

    list_display = ('name', 'status', 'model_artifact', 'input_image_path', 'created_at')
    search_fields = ('name', 'input_image_path', 'mask_path')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('model_artifact',)
    ordering = ('-created_at',)


@admin.register(TaskPoint)
class TaskPointAdmin(admin.ModelAdmin):
    """复查任务点后台管理配置。"""

    list_display = (
        'id',
        'mission',
        'disaster_category',
        'priority',
        'confidence',
        'status',
        'assigned_uav',
        'created_at',
    )
    search_fields = ('mission__name', 'assigned_uav__identifier')
    list_filter = ('disaster_category', 'status', 'created_at')
    list_editable = ('priority', 'status')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('mission', 'assigned_uav')
    ordering = ('-priority', 'id')


@admin.register(UAV)
class UAVAdmin(admin.ModelAdmin):
    """虚拟无人机后台管理配置。"""

    list_display = (
        'identifier',
        'name',
        'position_x',
        'position_y',
        'battery_level',
        'payload_capacity',
        'status',
        'updated_at',
    )
    search_fields = ('identifier', 'name')
    list_filter = ('status', 'created_at')
    list_editable = ('battery_level', 'status')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('identifier',)


@admin.register(SimulationRun)
class SimulationRunAdmin(admin.ModelAdmin):
    """调度仿真运行后台管理配置。"""

    list_display = (
        'id',
        'mission',
        'planning_method',
        'random_seed',
        'status',
        'started_at',
        'finished_at',
        'created_at',
    )
    search_fields = ('mission__name',)
    list_filter = ('planning_method', 'status', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('mission',)
    ordering = ('-created_at',)


@admin.register(SimulationEvent)
class SimulationEventAdmin(admin.ModelAdmin):
    """仿真事件后台管理配置。"""

    list_display = ('id', 'simulation_run', 'event_type', 'uav', 'task_point', 'occurred_at')
    search_fields = ('simulation_run__mission__name', 'uav__identifier')
    list_filter = ('event_type', 'occurred_at')
    readonly_fields = ('occurred_at',)
    autocomplete_fields = ('simulation_run', 'uav', 'task_point')
    ordering = ('-occurred_at',)


@admin.register(ExperimentResult)
class ExperimentResultAdmin(admin.ModelAdmin):
    """实验结果后台管理配置。"""

    list_display = (
        'id',
        'simulation_run',
        'baseline_method',
        'log_path',
        'result_file_path',
        'created_at',
    )
    search_fields = ('simulation_run__mission__name', 'log_path', 'result_file_path')
    list_filter = ('baseline_method', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('simulation_run',)
    ordering = ('-created_at',)

