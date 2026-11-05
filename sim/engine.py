"""推进状态、注入事件并触发动态重规划。"""

from __future__ import annotations

from planner.registry import replan
from planner.types import PlannerConfig

from .events import SimulationEvent
from .state import SimulationState


def apply_event(state: SimulationState, event: SimulationEvent | dict):
    event = SimulationEvent.from_mapping(event)
    if event.uav_id:
        for uav in state.uavs:
            if uav.id == event.uav_id:
                if event.event_type in {'uav_failure', 'failure'}:
                    uav.status = 'failed'
                elif event.event_type == 'low_battery':
                    uav.status = 'low_battery'
                    if 'battery_level' in event.payload:
                        uav.battery_level = float(event.payload['battery_level'])
    if event.event_type == 'task_added' and event.payload.get('task'):
        from planner.types import Task
        state.tasks.append(Task.from_mapping(event.payload['task']))
    return state


def replan_state(state: SimulationState, events, config=None):
    for event in events or []:
        apply_event(state, event)
    cfg = PlannerConfig.from_mapping(config)
    pending = [task for task in state.tasks if task.status not in {'completed', 'cancelled'}]
    result = replan(state.snapshot(), pending, [SimulationEvent.from_mapping(event).to_dict() for event in events or []], cfg.to_dict())
    state.routes = result.routes
    return result


