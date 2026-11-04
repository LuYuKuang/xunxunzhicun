"""core 应用的 JSON API 路由。"""

from django.urls import path

from . import api_views

app_name = 'core-api'

urlpatterns = [
    path('csrf/', api_views.csrf_token, name='csrf-token'),
    path('health/', api_views.health, name='health'),
    path('vision/infer/', api_views.vision_infer, name='vision-infer'),
    path('datasets/', api_views.datasets, name='datasets'),
    path('model-artifacts/', api_views.model_artifacts, name='model-artifacts'),
    path('missions/', api_views.missions, name='missions'),
    path('task-points/', api_views.task_points, name='task-points'),
    path('uavs/', api_views.uavs, name='uavs'),
    path('simulation-runs/', api_views.simulation_runs, name='simulation-runs'),
    path('simulation-runs/<int:simulation_id>/events/', api_views.simulation_events, name='simulation-events'),
    path('simulation-events/', api_views.all_simulation_events, name='simulation-events-all'),
    path('experiment-results/', api_views.experiment_results, name='experiment-results'),
]

