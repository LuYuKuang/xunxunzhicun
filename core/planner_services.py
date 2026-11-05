"""Django 与纯 Python planner/sim 之间的适配层。"""

from __future__ import annotations

from planner.registry import plan as run_plan
from planner.registry import replan as run_replan

from .models import SimulationEvent, SimulationRun, TaskPoint, UAV


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
    uavs = payload.get('uavs') or payload.get('uav_configuration') or all_uavs()
    if not tasks:
        raise ValueError('没有可调度任务，请先生成任务点或传入 tasks。')
    config = dict(payload.get('config') or {})
    config.update({key: payload[key] for key in ('algorithm', 'planning_method', 'random_seed') if key in payload})
    config['algorithm'] = config.get('algorithm') or config.get('planning_method') or 'risk_aware_pso'
    return run_plan(tasks, uavs, payload.get('map_state'), config)


def replan_simulation(simulation_run: SimulationRun, event_payload=None, config=None):
    event_payload = dict(event_payload or {})
    before = {
        'tasks': simulation_run.task_snapshot or [],
        'uavs': simulation_run.uav_configuration or [],
        'map_state': (simulation_run.summary_metrics or {}).get('map_state', {}),
        'routes': (simulation_run.summary_metrics or {}).get('routes', {}),
    }
    events = list(simulation_run.events.values('event_type', 'uav_id', 'task_point_id', 'state_after'))
    if event_payload:
        events.append(event_payload)
        if event_payload.get('event_type') == 'task_added' and event_payload.get('task'):
            before['tasks'].append(dict(event_payload['task']))
    pending = [item for item in before['tasks'] if item.get('status') not in {'completed', 'cancelled'}]
    cfg = dict(config or {})
    cfg.setdefault('algorithm', 'risk_aware_pso')
    cfg.setdefault('random_seed', simulation_run.random_seed)
    result = run_replan(before, pending, events, cfg)
    summary = dict(simulation_run.summary_metrics or {})
    summary.update(result.to_dict())
    summary['map_state'] = before['map_state']
    updated_uavs = [dict(item) for item in before['uavs']]
    if event_payload.get('uav_id') and event_payload.get('event_type') in {'uav_failure', 'failure', 'low_battery'}:
        for item in updated_uavs:
            if str(item.get('identifier', item.get('id'))) == str(event_payload['uav_id']):
                item['status'] = 'failed' if event_payload['event_type'] in {'uav_failure', 'failure'} else 'low_battery'
    simulation_run.uav_configuration = updated_uavs
    simulation_run.summary_metrics = summary
    simulation_run.status = SimulationRun.Status.RUNNING
    simulation_run.save(update_fields=['uav_configuration', 'summary_metrics', 'status', 'updated_at'])
    return result, before, summary


