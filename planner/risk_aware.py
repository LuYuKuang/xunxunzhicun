"""风险加权 PSO 和事件后的局部重规划。"""

from __future__ import annotations

import time

from .pso import pso
from .types import MapState, PlannerConfig, Task, UAVState


def risk_aware_pso(tasks, uavs, map_state, config):
    config.weights = dict(config.weights)
    config.weights.update({'time': 1.25, 'risk_delay': 4.0, 'balance': 0.75})
    result = pso(tasks, uavs, map_state, config, algorithm='risk_aware_pso@1')
    result.metrics['risk_weighted'] = True
    return result


def replan(current_state, pending_tasks, events, config):
    started = time.perf_counter()
    state = dict(current_state or {})
    map_state = MapState.from_mapping(state.get('map_state'))
    defaults = dict(config.default_uav)
    uavs = [UAVState.from_mapping(item, defaults) for item in state.get('uavs', [])]
    tasks = [Task.from_mapping(item) for item in pending_tasks]
    for event in events or []:
        event_type = str(event.get('event_type', event.get('type', '')))
        failed_id = event.get('uav_id') or event.get('failed_uav')
        if failed_id:
            for uav in uavs:
                if uav.id == str(failed_id) or event_type in {'uav_failure', 'failure'} and uav.id == str(failed_id):
                    uav.status = 'failed'
        if event_type == 'low_battery' and failed_id:
            for uav in uavs:
                if uav.id == str(failed_id):
                    uav.status = 'low_battery'
    result = risk_aware_pso(tasks, uavs, map_state, config)
    result.algorithm = 'risk_aware_pso@1:replan'
    result.metrics.update({
        'replanning_ms': round((time.perf_counter() - started) * 1000, 3),
        'affected_task_count': len(tasks),
        'event_count': len(events or []),
        'recovery_rate': result.metrics.get('completion_rate', 0.0),
    })
    return result


