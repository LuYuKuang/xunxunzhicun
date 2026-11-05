"""统一计划指标和目标函数。"""

from __future__ import annotations

import math
from collections import defaultdict

from .cost import evaluate_route, task_risk
from .types import MapState, PlanResult, PlannerConfig, Task, UAVState


def make_result(routes, tasks, uavs, map_state, config, algorithm, violations=None, status=None):
    task_map = {task.id: task for task in tasks}
    uav_map = {uav.id: uav for uav in uavs}
    assignments = {str(uav_id): [str(task_id) for task_id in task_ids] for uav_id, task_ids in routes.items()}
    route_payload = {}
    all_violations = list(violations or [])
    distances = []
    times = []
    energies = []
    risk_delay = 0.0
    assigned = set()
    for uav_id, task_ids in assignments.items():
        uav = uav_map.get(uav_id)
        if uav is None:
            all_violations.append({'type': 'unknown_uav', 'uav_id': uav_id})
            continue
        sequence = [task_map[task_id] for task_id in task_ids if task_id in task_map]
        assigned.update(task.id for task in sequence)
        result = evaluate_route(sequence, uav, map_state, config)
        all_violations.extend(result['violations'])
        distances.append(result['distance'])
        times.append(result['time'])
        energies.append(result['energy'])
        risk_delay += result['risk_delay']
        route_payload[uav_id] = {
            'start': {'x': result['points'][0][0], 'y': result['points'][0][1]},
            'tasks': [
                {'task_id': task.id, 'x': task.x, 'y': task.y, 'category': task.category,
                 'priority': task.priority, 'confidence': task.confidence}
                for task in sequence
            ],
            'return': ({'x': result['points'][-1][0], 'y': result['points'][-1][1]} if result['points'] else None),
            'distance': round(result['distance'], 6),
            'time': round(result['time'], 6),
        }
    pending = [task for task in tasks if task.status not in {'completed', 'cancelled'}]
    unassigned = [task for task in pending if task.id not in assigned]
    if unassigned:
        all_violations.extend({'type': 'unassigned', 'task_id': task.id, 'message': '任务未分配'} for task in unassigned)
    total_distance = sum(distances)
    total_time = max(times, default=0.0)
    total_energy = sum(energies)
    average_distance = total_distance / max(1, len(distances))
    balance = math.sqrt(sum((value - average_distance) ** 2 for value in distances) / max(1, len(distances)))
    completed = len(assigned)
    target_count = len(pending)
    priority_sum = sum(task_risk(task) for task in pending) or 1.0
    focused = sum(task_risk(task) for task in pending if task.id in assigned)
    metrics = {
        'completion_rate': completed / max(1, target_count),
        'focus_task_completion_rate': focused / priority_sum,
        'recovery_rate': completed / max(1, target_count),
        'total_distance': round(total_distance, 6),
        'total_time': round(total_time, 6),
        'total_energy': round(total_energy, 6),
        'risk_delay': round(risk_delay, 6),
        'load_imbalance': round(balance, 6),
        'assigned_count': completed,
        'unassigned_count': len(unassigned),
        'constraint_violations': len(all_violations),
        'repair_count': sum(1 for item in all_violations if item.get('type') == 'repair'),
    }
    weights = config.weights
    objective = (
        weights.get('time', 1.0) * total_time
        + weights.get('distance', 0.35) * total_distance
        + weights.get('energy', 0.25) * total_energy
        + weights.get('risk_delay', 2.0) * risk_delay
        + weights.get('balance', 0.5) * balance
        + config.penalty * len(all_violations)
    )
    result_status = status or ('partial' if unassigned else ('repaired' if all_violations else 'feasible'))
    return PlanResult(
        assignments=assignments,
        routes=route_payload,
        objective_value=round(objective, 6),
        metrics=metrics,
        violations=all_violations,
        random_seed=config.random_seed,
        algorithm=algorithm,
        status=result_status,
        config=config.to_dict(),
    )


