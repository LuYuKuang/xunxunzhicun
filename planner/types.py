"""调度模块的输入、配置和输出数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


@dataclass(frozen=True)
class Task:
    id: str
    x: float
    y: float
    category: str = 'flooded_area'
    area: float = 1.0
    confidence: float = 1.0
    uncertainty: float | None = None
    priority: float = 0.0
    service_time: float = 1.0
    deadline: float | None = None
    status: str = 'pending'
    payload: float = 0.0

    @classmethod
    def from_mapping(cls, value: Any) -> 'Task':
        if isinstance(value, cls):
            return value
        item = dict(value or {})
        confidence = max(0.0, min(1.0, _float(item.get('confidence'), 1.0)))
        uncertainty = item.get('uncertainty')
        uncertainty = 1.0 - confidence if uncertainty is None else max(0.0, min(1.0, _float(uncertainty)))
        deadline = item.get('deadline')
        return cls(
            id=str(item.get('id', item.get('task_id', ''))),
            x=_float(item.get('x', item.get('coordinate_x'))),
            y=_float(item.get('y', item.get('coordinate_y'))),
            category=str(item.get('category', item.get('disaster_category', 'flooded_area'))),
            area=max(0.0, _float(item.get('area'), 1.0)),
            confidence=confidence,
            uncertainty=uncertainty,
            priority=max(0.0, _float(item.get('priority'))),
            service_time=max(0.0, _float(item.get('service_time'), 1.0)),
            deadline=None if deadline in (None, '') else max(0.0, _float(deadline)),
            status=str(item.get('status', 'pending')),
            payload=max(0.0, _float(item.get('payload'))),
        )

    def risk_score(self) -> float:
        severity = {
            'flooded_building': 3.0,
            'flooded_road': 3.0,
            'flooded_area': 2.0,
            'water': 1.5,
        }.get(self.category, 1.0)
        base = self.priority if self.priority > 0 else severity * max(1.0, self.area)
        return base * max(0.05, self.uncertainty or 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id, 'x': self.x, 'y': self.y, 'category': self.category,
            'area': self.area, 'confidence': self.confidence, 'uncertainty': self.uncertainty,
            'priority': self.priority, 'service_time': self.service_time, 'deadline': self.deadline,
            'status': self.status, 'payload': self.payload,
        }


@dataclass
class UAVState:
    id: str
    x: float = 0.0
    y: float = 0.0
    battery_level: float = 100.0
    battery_reserve: float = 20.0
    speed: float = 10.0
    payload_capacity: float = 100.0
    max_range: float | None = None
    status: str = 'idle'
    payload_used: float = 0.0
    home_x: float | None = None
    home_y: float | None = None

    @classmethod
    def from_mapping(cls, value: Any, defaults: dict[str, Any] | None = None) -> 'UAVState':
        if isinstance(value, cls):
            return value
        item = dict(defaults or {})
        item.update(dict(value or {}))
        home = item.get('home') or {}
        home_x = home.get('x', item.get('home_x'))
        home_y = home.get('y', item.get('home_y'))
        return cls(
            id=str(item.get('id', item.get('identifier', ''))),
            x=_float(item.get('x', item.get('position_x'))),
            y=_float(item.get('y', item.get('position_y'))),
            battery_level=max(0.0, min(100.0, _float(item.get('battery_level', item.get('battery')), 100))),
            battery_reserve=max(0.0, _float(item.get('battery_reserve', item.get('return_margin')), 20)),
            speed=max(0.01, _float(item.get('speed'), 10)),
            payload_capacity=max(0.0, _float(item.get('payload_capacity'), 100)),
            max_range=None if item.get('max_range') in (None, '') else max(0.0, _float(item.get('max_range'))),
            status=str(item.get('status', 'idle')),
            payload_used=max(0.0, _float(item.get('payload_used'))),
            home_x=None if home_x is None else _float(home_x),
            home_y=None if home_y is None else _float(home_y),
        )

    @property
    def available(self) -> bool:
        return self.status not in {'failed', 'offline', 'fault', 'low_battery'} and self.battery_level > self.battery_reserve

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id, 'x': self.x, 'y': self.y, 'battery_level': self.battery_level,
            'battery_reserve': self.battery_reserve, 'speed': self.speed,
            'payload_capacity': self.payload_capacity, 'max_range': self.max_range,
            'status': self.status, 'payload_used': self.payload_used,
            'home': {axis: value for axis, value in (('x', self.home_x), ('y', self.home_y)) if value is not None},
        }


@dataclass
class MapState:
    width: float = 100.0
    height: float = 100.0
    home_x: float = 0.0
    home_y: float = 0.0
    obstacles: list[list[tuple[float, float]]] = field(default_factory=list)
    no_fly_zones: list[list[tuple[float, float]]] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, value: Any) -> 'MapState':
        if isinstance(value, cls):
            return value
        item = dict(value or {})
        home = item.get('home') or item.get('takeoff_point') or {}

        def polygon_list(raw):
            result = []
            for polygon in raw or []:
                points = []
                for point in polygon:
                    if isinstance(point, dict):
                        points.append((_float(point.get('x')), _float(point.get('y'))))
                    else:
                        points.append((_float(point[0]), _float(point[1])))
                if len(points) >= 3:
                    result.append(points)
            return result

        return cls(
            width=max(1.0, _float(item.get('width'), 100)),
            height=max(1.0, _float(item.get('height'), 100)),
            home_x=_float(home.get('x'), _float(item.get('home_x'))),
            home_y=_float(home.get('y'), _float(item.get('home_y'))),
            obstacles=polygon_list(item.get('obstacles')),
            no_fly_zones=polygon_list(item.get('no_fly_zones', item.get('restricted_zones'))),
        )

    def to_dict(self):
        return {
            'width': self.width, 'height': self.height,
            'home': {'x': self.home_x, 'y': self.home_y},
            'obstacles': [[list(point) for point in polygon] for polygon in self.obstacles],
            'no_fly_zones': [[list(point) for point in polygon] for polygon in self.no_fly_zones],
        }


@dataclass
class PlannerConfig:
    algorithm: str = 'risk_aware_pso'
    random_seed: int = 42
    population_size: int = 24
    iterations: int = 40
    inertia: float = 0.72
    cognitive: float = 1.35
    social: float = 1.45
    # 地图坐标按仿真米计，默认每米消耗 0.08 个百分点电量。
    energy_per_distance: float = 0.08
    return_to_home: bool = True
    penalty: float = 10000.0
    weights: dict[str, float] = field(default_factory=lambda: {
        'time': 1.0, 'distance': 0.35, 'energy': 0.25,
        'risk_delay': 2.0, 'balance': 0.5,
    })
    default_uav: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Any) -> 'PlannerConfig':
        item = dict(value or {})
        weights = dict(cls().weights)
        weights.update(item.get('weights') or {})
        return cls(
            algorithm=str(item.get('algorithm', 'risk_aware_pso')),
            random_seed=_int(item.get('random_seed'), 42),
            population_size=max(4, _int(item.get('population_size'), 24)),
            iterations=max(1, _int(item.get('iterations'), 40)),
            inertia=_float(item.get('inertia'), 0.72),
            cognitive=_float(item.get('cognitive'), 1.35),
            social=_float(item.get('social'), 1.45),
            energy_per_distance=max(0.001, _float(item.get('energy_per_distance'), 0.08)),
            return_to_home=bool(item.get('return_to_home', True)),
            penalty=max(1.0, _float(item.get('penalty'), 10000)),
            weights=weights,
            default_uav=dict(item.get('default_uav') or {}),
        )

    def to_dict(self):
        return {
            'algorithm': self.algorithm, 'random_seed': self.random_seed,
            'population_size': self.population_size, 'iterations': self.iterations,
            'inertia': self.inertia, 'cognitive': self.cognitive, 'social': self.social,
            'energy_per_distance': self.energy_per_distance, 'return_to_home': self.return_to_home,
            'penalty': self.penalty, 'weights': dict(self.weights), 'default_uav': dict(self.default_uav),
        }


@dataclass
class PlanResult:
    assignments: dict[str, list[str]]
    routes: dict[str, dict[str, Any]]
    objective_value: float
    metrics: dict[str, Any]
    violations: list[dict[str, Any]]
    random_seed: int
    algorithm: str
    status: str = 'feasible'
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            'assignments': self.assignments,
            'routes': self.routes,
            'objective_value': self.objective_value,
            'metrics': self.metrics,
            'violations': self.violations,
            'random_seed': self.random_seed,
            'algorithm': self.algorithm,
            'status': self.status,
            'config': self.config,
        }

