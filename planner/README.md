# 调度模块

调度器完全独立于 Django 和视觉模型，入口是：

```python
from planner import plan, replan

result = plan(tasks, uavs, map_state, {'algorithm': 'risk_aware_pso', 'random_seed': 42})
next_result = replan(current_state, pending_tasks, events, {'algorithm': 'risk_aware_pso'})
```

稳定算法名称为 `round_robin`、`nearest`、`pso` 和 `risk_aware_pso`。输出的 `PlanResult.to_dict()` 可以直接写入 `SimulationRun.summary_metrics`。Django 通过 `POST /api/plans/preview/` 调用首轮计划，通过 `POST /api/simulation-runs/{id}/replan/` 记录事件并重规划。


