"""调度器的统一协议。"""

from __future__ import annotations

from typing import Protocol, Sequence, Any

from .types import MapState, PlanResult, PlannerConfig, Task, UAVState


class Planner(Protocol):
    name: str

    def plan(
        self,
        tasks: Sequence[Task],
        uavs: Sequence[UAVState],
        map_state: MapState,
        config: PlannerConfig,
    ) -> PlanResult: ...

    def replan(
        self,
        current_state: Any,
        pending_tasks: Sequence[Task],
        events: Sequence[dict[str, Any]],
        config: PlannerConfig,
    ) -> PlanResult: ...


