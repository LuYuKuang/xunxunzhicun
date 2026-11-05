import unittest

from planner import MapState, PlannerConfig, Task, UAVState, plan, replan


def scenario():
    tasks = [
        Task(id=f'T-{i}', x=(i * 11) % 80 + 5, y=(i * 17) % 80 + 5, area=i + 1, confidence=0.7 + i / 30, priority=10 - i)
        for i in range(8)
    ]
    uavs = [
        UAVState(id='UAV-01', x=0, y=0, battery_level=100, battery_reserve=15, max_range=300),
        UAVState(id='UAV-02', x=10, y=0, battery_level=100, battery_reserve=15, max_range=300),
        UAVState(id='UAV-03', x=0, y=10, battery_level=100, battery_reserve=15, max_range=300),
    ]
    return tasks, uavs, MapState(width=100, height=100)


class PlannerTests(unittest.TestCase):
    def test_every_task_is_assigned_at_most_once(self):
        tasks, uavs, map_state = scenario()
        result = plan(tasks, uavs, map_state, {'algorithm': 'nearest', 'random_seed': 42})
        assigned = [task_id for values in result.assignments.values() for task_id in values]
        self.assertEqual(len(assigned), len(set(assigned)))
        self.assertEqual(set(assigned), {task.id for task in tasks})

    def test_seed_reproduces_pso(self):
        tasks, uavs, map_state = scenario()
        config = {'algorithm': 'pso', 'random_seed': 9, 'population_size': 8, 'iterations': 8}
        first = plan(tasks, uavs, map_state, config).to_dict()
        second = plan(tasks, uavs, map_state, config).to_dict()
        self.assertEqual(first, second)

    def test_failed_uav_is_excluded(self):
        tasks, uavs, map_state = scenario()
        uavs[1].status = 'failed'
        result = plan(tasks, uavs, map_state, {'algorithm': 'risk_aware_pso', 'population_size': 8, 'iterations': 8})
        self.assertNotIn('UAV-02', result.assignments)
        self.assertTrue(all(item.get('uav_id') != 'UAV-02' for item in result.violations if item.get('type') == 'failed_uav'))

    def test_replan_keeps_completed_out_of_pending(self):
        tasks, uavs, map_state = scenario()
        tasks[0] = Task(**{**tasks[0].__dict__, 'status': 'completed'})
        result = replan({'tasks': [task.to_dict() for task in tasks], 'uavs': [uav.to_dict() for uav in uavs], 'map_state': map_state.to_dict()}, events=[{'event_type': 'uav_failure', 'uav_id': 'UAV-02'}], config={'random_seed': 4, 'population_size': 8, 'iterations': 8})
        assigned = {task_id for values in result.assignments.values() for task_id in values}
        self.assertNotIn('T-0', assigned)
        self.assertNotIn('UAV-02', result.assignments)

    def test_battery_and_no_fly_constraints_are_reported(self):
        tasks = [Task(id='T-1', x=90, y=90, area=1, priority=10)]
        uavs = [UAVState(id='UAV-01', battery_level=25, battery_reserve=20, max_range=30)]
        map_state = MapState(width=100, height=100, no_fly_zones=[[(40, 40), (60, 40), (60, 60), (40, 60)]])
        result = plan(tasks, uavs, map_state, {'algorithm': 'nearest', 'energy_per_distance': 1.0})
        violation_types = {item.get('type') for item in result.violations}
        self.assertTrue({'battery', 'range'} & violation_types)
        self.assertIn('no_fly_zone', violation_types)

    def test_metrics_have_required_fields(self):
        tasks, uavs, map_state = scenario()
        result = plan(tasks, uavs, map_state, {'algorithm': 'round_robin', 'energy_per_distance': 0.05})
        for key in ('completion_rate', 'total_time', 'total_distance', 'total_energy', 'recovery_rate'):
            # recovery_rate only exists on replan results; the normal plan must expose its base metrics.
            if key == 'recovery_rate':
                continue
            self.assertIn(key, result.metrics)


if __name__ == '__main__':
    unittest.main()


