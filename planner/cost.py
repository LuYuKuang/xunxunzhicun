"""几何、能耗、风险迟延和约束代价。"""

from __future__ import annotations

import math
from typing import Iterable

from .types import MapState, PlannerConfig, Task, UAVState


def distance(a, b) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _inside_polygon(point, polygon):
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        intersects = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi)
        if intersects:
            inside = not inside
        j = i
    return inside


def segment_intersects_zones(a, b, zones) -> bool:
    length = distance(a, b)
    steps = max(2, int(length / 2.0) + 1)
    for index in range(steps + 1):
        ratio = index / steps
        point = (a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio)
        if any(_inside_polygon(point, polygon) for polygon in zones):
            return True
    return False


def in_bounds(point, map_state: MapState) -> bool:
    return 0.0 <= point[0] <= map_state.width and 0.0 <= point[1] <= map_state.height


def task_risk(task: Task) -> float:
    return task.risk_score()


def evaluate_route(
    task_sequence: Iterable[Task],
    uav: UAVState,
    map_state: MapState,
    config: PlannerConfig,
) -> dict:
    tasks = list(task_sequence)
    start = (uav.x, uav.y)
    home = (uav.home_x if uav.home_x is not None else map_state.home_x, uav.home_y if uav.home_y is not None else map_state.home_y)
    points = [start] + [(task.x, task.y) for task in tasks]
    if config.return_to_home:
        points.append(home)
    total_distance = sum(distance(points[i], points[i + 1]) for i in range(len(points) - 1))
    service_time = sum(task.service_time for task in tasks)
    time_cost = total_distance / max(0.01, uav.speed) + service_time
    energy = total_distance * config.energy_per_distance
    violations = []
    for task in tasks:
        if not in_bounds((task.x, task.y), map_state):
            violations.append({'type': 'boundary', 'task_id': task.id, 'message': '任务点超出地图边界'})
        if task.payload + uav.payload_used > uav.payload_capacity:
            violations.append({'type': 'payload', 'task_id': task.id, 'message': '载荷能力不足'})
    if uav.max_range is not None and total_distance > uav.max_range + 1e-9:
        violations.append({'type': 'range', 'uav_id': uav.id, 'message': '超过最大航程', 'value': total_distance})
    available_energy = max(0.0, uav.battery_level - uav.battery_reserve)
    if energy > available_energy + 1e-9:
        violations.append({'type': 'battery', 'uav_id': uav.id, 'message': '扣除返航余量后电量不足', 'value': energy})
    for task in tasks:
        if task.deadline is not None and time_cost > task.deadline + 1e-9:
            violations.append({'type': 'deadline', 'task_id': task.id, 'message': '任务超过截止时间', 'value': time_cost})
    for index in range(len(points) - 1):
        if segment_intersects_zones(points[index], points[index + 1], map_state.no_fly_zones):
            violations.append({'type': 'no_fly_zone', 'uav_id': uav.id, 'message': '航段穿过禁飞区', 'segment': index})
        if segment_intersects_zones(points[index], points[index + 1], map_state.obstacles):
            violations.append({'type': 'obstacle', 'uav_id': uav.id, 'message': '航段穿过障碍区域', 'segment': index})
    elapsed = 0.0
    risk_delay = 0.0
    for task in tasks:
        elapsed += task.service_time
        if task.deadline is not None:
            risk_delay += max(0.0, time_cost - task.deadline) * task_risk(task)
    return {
        'distance': total_distance, 'time': time_cost, 'energy': energy,
        'risk_delay': risk_delay, 'violations': violations,
        'points': points,
    }


