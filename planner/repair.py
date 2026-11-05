"""统一的解码和不可行解修复逻辑。"""

from __future__ import annotations

from .cost import evaluate_route
from .types import MapState, PlannerConfig, Task, UAVState


def repair_routes(routes, tasks, uavs, map_state, config):
    task_map = {task.id: task for task in tasks}
    uav_map = {uav.id: uav for uav in uavs}
    repaired = {uav.id: [] for uav in uavs if uav.available}
    seen = set()
    violations = []
    for raw_uav_id, raw_task_ids in (routes or {}).items():
        uav_id = str(raw_uav_id)
        if uav_id not in repaired:
            if raw_task_ids:
                violations.append({'type': 'failed_uav', 'uav_id': uav_id, 'message': '故障或离线无人机被排除'})
            continue
        for raw_task_id in raw_task_ids:
            task_id = str(raw_task_id)
            if task_id not in task_map:
                violations.append({'type': 'unknown_task', 'task_id': task_id})
                continue
            if task_id in seen:
                violations.append({'type': 'duplicate_task', 'task_id': task_id})
                continue
            if task_map[task_id].status in {'completed', 'cancelled'}:
                continue
            repaired[uav_id].append(task_id)
            seen.add(task_id)

    pending = [task for task in tasks if task.status not in {'completed', 'cancelled'} and task.id not in seen]
    pending.sort(key=lambda task: (-task_risk_key(task), str(task.id)))
    for task in pending:
        candidates = []
        for uav_id, task_ids in repaired.items():
            uav = uav_map[uav_id]
            sequence = [task_map[item] for item in task_ids] + [task]
            result = evaluate_route(sequence, uav, map_state, config)
            candidates.append((len(result['violations']), result['distance'], uav_id))
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1], item[2]))
            violation_count, _, uav_id = candidates[0]
            repaired[uav_id].append(task.id)
            seen.add(task.id)
            if violation_count:
                violations.append({'type': 'repair', 'task_id': task.id, 'uav_id': uav_id, 'message': '任务已分配但仍有约束风险'})
        else:
            violations.append({'type': 'unassigned', 'task_id': task.id, 'message': '没有可用无人机'})
    return repaired, violations


def task_risk_key(task):
    return task.risk_score()


