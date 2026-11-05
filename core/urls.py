"""core 应用的 JSON API 路由。"""

from django.urls import path

from . import api_views

app_name = 'core-api'

urlpatterns = [
    path('csrf/', api_views.csrf_token, name='csrf-token'),
    path('health/', api_views.health, name='health'),
    path('plans/preview/', api_views.plans_preview, name='plans-preview'),
    path('tasks/generate/', api_views.task_generate, name='tasks-generate'),
    path('images/upload/', api_views.upload_image, name='image-upload'),
    path('vision/infer/', api_views.vision_infer, name='vision-infer'),
    path('disaster-categories/', api_views.disaster_categories, name='disaster-categories'),
    path('datasets/', api_views.datasets, name='datasets'),
    path('model-artifacts/', api_views.model_artifacts, name='model-artifacts'),
    path('missions/', api_views.missions, name='missions'),
    path('missions/<int:mission_id>/', api_views.mission_detail, name='mission-detail'),
    path('task-points/', api_views.task_points, name='task-points'),
    path('task-points/<int:task_point_id>/', api_views.task_point_detail, name='task-point-detail'),
    path('uavs/', api_views.uavs, name='uavs'),
    path('simulation-runs/', api_views.simulation_runs, name='simulation-runs'),
    path('simulation-runs/<int:simulation_id>/events/', api_views.simulation_events, name='simulation-events'),
    path('simulation-runs/<int:simulation_id>/replan/', api_views.simulation_replan, name='simulation-replan'),
    path('simulation-events/', api_views.all_simulation_events, name='simulation-events-all'),
    path('experiment-results/', api_views.experiment_results, name='experiment-results'),
]

