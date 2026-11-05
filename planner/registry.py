"""稳定名称到调度实现的注册表。"""

from __future__ import annotations

from .baseline import nearest, round_robin
from .pso import pso
from .risk_aware import replan as risk_replan, risk_aware_pso
from .types import MapState, PlannerConfig, Task, UAVState

PLANNER_NAMES = ('round_robin', 'nearest', 'pso', 'risk_aware_pso')


def _coerce(tasks, uavs, map_state, config):
    cfg = PlannerConfig.from_mapping(config)
    task_items = [Task.from_mapping(item) for item in tasks or []]
    uav_items = [UAVState.from_mapping(item, cfg.default_uav) for item in uavs or []]
    return task_items, uav_items, MapState.from_mapping(map_state), cfg


def plan(tasks, uavs, map_state=None, config=None):
    task_items, uav_items, map_items, cfg = _coerce(tasks, uavs, map_state, config)
    name = cfg.algorithm.lower()
    if name == 'round_robin':
        return round_robin(task_items, uav_items, map_items, cfg)
    if name == 'nearest':
        return nearest(task_items, uav_items, map_items, cfg)
    if name == 'pso':
        return pso(task_items, uav_items, map_items, cfg)
    if name == 'risk_aware_pso':
        return risk_aware_pso(task_items, uav_items, map_items, cfg)
    raise ValueError(f'不支持的调度算法：{cfg.algorithm}，可选值为 {PLANNER_NAMES}')


def replan(current_state, pending_tasks=None, events=None, config=None):
    cfg = PlannerConfig.from_mapping(config)
    state = dict(current_state or {})
    task_items = pending_tasks if pending_tasks is not None else [
        item for item in state.get('tasks', [])
        if str(item.get('status', 'pending')) not in {'completed', 'cancelled'}
    ]
    return risk_replan(state, task_items, events or [], cfg)


