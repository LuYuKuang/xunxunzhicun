"""不依赖 Django 的仿真状态快照。"""

from __future__ import annotations

from dataclasses import dataclass, field

from planner.types import MapState, Task, UAVState


@dataclass
class SimulationState:
    tasks: list[Task] = field(default_factory=list)
    uavs: list[UAVState] = field(default_factory=list)
    map_state: MapState = field(default_factory=MapState)
    routes: dict = field(default_factory=dict)
    elapsed_time: float = 0.0

    @classmethod
    def from_mapping(cls, value):
        value = dict(value or {})
        return cls(
            tasks=[Task.from_mapping(item) for item in value.get('tasks', value.get('task_snapshot', []))],
            uavs=[UAVState.from_mapping(item) for item in value.get('uavs', value.get('uav_configuration', []))],
            map_state=MapState.from_mapping(value.get('map_state')),
            routes=dict(value.get('routes') or {}),
            elapsed_time=float(value.get('elapsed_time', 0.0) or 0.0),
        )

    def snapshot(self):
        return {
            'tasks': [task.to_dict() for task in self.tasks],
            'uavs': [uav.to_dict() for uav in self.uavs],
            'map_state': self.map_state.to_dict(),
            'routes': self.routes,
            'elapsed_time': self.elapsed_time,
        }


