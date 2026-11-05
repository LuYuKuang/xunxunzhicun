"""可解释的基线调度算法。"""

from .evaluate import make_result
from .repair import repair_routes


def _active(tasks):
    return sorted((task for task in tasks if task.status not in {'completed', 'cancelled'}), key=lambda item: (-item.risk_score(), str(item.id)))


def round_robin(tasks, uavs, map_state, config):
    active = [uav for uav in uavs if uav.available]
    routes = {uav.id: [] for uav in active}
    if active:
        for index, task in enumerate(_active(tasks)):
            routes[active[index % len(active)].id].append(task.id)
    routes, violations = repair_routes(routes, tasks, uavs, map_state, config)
    return make_result(routes, tasks, uavs, map_state, config, 'round_robin@1', violations)


def nearest(tasks, uavs, map_state, config):
    active = [uav for uav in uavs if uav.available]
    routes = {uav.id: [] for uav in active}
    task_map = {task.id: task for task in tasks}
    for task in _active(tasks):
        choices = []
        for uav in active:
            from .cost import evaluate_route
            candidate = [task_map[item] for item in routes[uav.id]] + [task]
            score = evaluate_route(candidate, uav, map_state, config)
            choices.append((len(score['violations']), score['distance'], uav.id))
        if choices:
            choices.sort(key=lambda item: (item[0], item[1], item[2]))
            routes[choices[0][2]].append(task.id)
    routes, violations = repair_routes(routes, tasks, uavs, map_state, config)
    return make_result(routes, tasks, uavs, map_state, config, 'nearest@1', violations)


