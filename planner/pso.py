"""标准离散 PSO：任务分配得分 + 每架无人机任务顺序得分。"""

from __future__ import annotations

import random

from .baseline import nearest
from .evaluate import make_result
from .repair import repair_routes


def _decode(task_ids, active_uavs, assignment_scores, order_scores):
    routes = {uav_id: [] for uav_id in active_uavs}
    if not active_uavs:
        return routes
    for index, task_id in enumerate(task_ids):
        uav_index = max(range(len(active_uavs)), key=lambda candidate: assignment_scores[index][candidate])
        routes[active_uavs[uav_index]].append((order_scores[index], task_id))
    return {uav_id: [task_id for _, task_id in sorted(items)] for uav_id, items in routes.items()}


def pso(tasks, uavs, map_state, config, algorithm='pso@1'):
    active = [uav for uav in uavs if uav.available]
    task_items = [task for task in tasks if task.status not in {'completed', 'cancelled'}]
    task_ids = [task.id for task in task_items]
    if not task_ids or not active:
        return make_result({uav.id: [] for uav in active}, tasks, uavs, map_state, config, algorithm, [{'type': 'unassigned', 'message': '无任务或无可用无人机'}] if task_items else [])
    rng = random.Random(config.random_seed)
    count = len(task_ids)
    width = len(active)
    particles = []
    global_best = None
    global_value = float('inf')

    def evaluate_particle(particle):
        routes = _decode(task_ids, [uav.id for uav in active], particle['a'], particle['o'])
        repaired, _ = repair_routes(routes, tasks, uavs, map_state, config)
        return make_result(repaired, tasks, uavs, map_state, config, algorithm)

    for _ in range(config.population_size):
        particle = {
            'a': [[rng.uniform(-1, 1) for _ in range(width)] for _ in range(count)],
            'av': [[0.0 for _ in range(width)] for _ in range(count)],
            'o': [rng.random() for _ in range(count)],
            'ov': [0.0 for _ in range(count)],
        }
        result = evaluate_particle(particle)
        particle['best_a'] = [row[:] for row in particle['a']]
        particle['best_av'] = [row[:] for row in particle['av']]
        particle['best_o'] = particle['o'][:]
        particle['best_ov'] = particle['ov'][:]
        particle['best_value'] = result.objective_value
        particles.append(particle)
        if result.objective_value < global_value:
            global_value, global_best = result.objective_value, result

    for _ in range(config.iterations):
        for particle in particles:
            for i in range(count):
                for j in range(width):
                    r1, r2 = rng.random(), rng.random()
                    global_target = 0.0
                    if global_best and task_ids[i] in global_best.assignments.get(str(active[j].id), []):
                        global_target = 1.0
                    elif global_best:
                        global_target = -1.0
                    particle['av'][i][j] = (
                        config.inertia * particle['av'][i][j]
                        + config.cognitive * r1 * (particle['best_a'][i][j] - particle['a'][i][j])
                        + config.social * r2 * (global_target - particle['a'][i][j])
                    )
                    particle['av'][i][j] = max(-4.0, min(4.0, particle['av'][i][j]))
                    particle['a'][i][j] += particle['av'][i][j]
                r1, r2 = rng.random(), rng.random()
                particle['ov'][i] = config.inertia * particle['ov'][i] + config.cognitive * r1 * (particle['best_o'][i] - particle['o'][i]) + config.social * r2 * (rng.random() - particle['o'][i])
                particle['o'][i] = (particle['o'][i] + particle['ov'][i]) % 1.0
            result = evaluate_particle(particle)
            if result.objective_value < particle['best_value']:
                particle['best_value'] = result.objective_value
                particle['best_a'] = [row[:] for row in particle['a']]
                particle['best_o'] = particle['o'][:]
            if result.objective_value < global_value:
                global_value, global_best = result.objective_value, result
    return global_best


