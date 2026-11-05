"""仿真事件数据结构。"""

from dataclasses import dataclass, field


@dataclass
class SimulationEvent:
    event_type: str
    uav_id: str | None = None
    task_id: str | None = None
    payload: dict = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value):
        value = dict(value or {})
        return cls(
            event_type=str(value.get('event_type', value.get('type', ''))),
            uav_id=str(value['uav_id']) if value.get('uav_id') is not None else None,
            task_id=str(value['task_id']) if value.get('task_id') is not None else None,
            payload=dict(value.get('payload') or value.get('state_after') or {}),
        )

    def to_dict(self):
        return {'event_type': self.event_type, 'uav_id': self.uav_id, 'task_id': self.task_id, 'payload': self.payload}


