import json
import shutil
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import TestCase, override_settings
from PIL import Image

from .models import Dataset, Mission, SimulationRun, TaskPoint


class CoreApiTests(TestCase):
    """验证核心 API 的数据库读写、图片上传和健康检查。"""

    def setUp(self):
        self.media_root = Path(settings.BASE_DIR) / '.test_media'
        shutil.rmtree(self.media_root, ignore_errors=True)
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.dataset = Dataset.objects.create(
            name='FloodNet',
            source_url='https://example.com/floodnet',
            license_name='MIT',
            version='test-v1',
            categories=['受淹道路', '受淹建筑'],
            local_index_path='indexes/test.json',
        )

    def tearDown(self):
        shutil.rmtree(self.media_root, ignore_errors=True)
        super().tearDown()

    def test_health_checks_database(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['success'])
        self.assertEqual(body['data']['database'], 'ok')
        self.assertIn('model', body['data'])

    def test_django_admin_login_is_available(self):
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)

    def test_create_and_filter_mission_and_task_point(self):
        mission_response = self.client.post(
            '/api/missions/',
            data=json.dumps({'name': '测试复查任务', 'input_image_path': 'missions/input.jpg'}),
            content_type='application/json',
        )
        self.assertEqual(mission_response.status_code, 201)
        mission_id = mission_response.json()['data']['id']

        task_response = self.client.post(
            '/api/task-points/',
            data=json.dumps({
                'mission_id': mission_id,
                'coordinate_x': 12.5,
                'coordinate_y': 8,
                'disaster_category': 'flooded_road',
                'area': 32.4,
                'confidence': 0.91,
                'priority': 4,
            }),
            content_type='application/json',
        )
        self.assertEqual(task_response.status_code, 201)
        task_id = task_response.json()['data']['id']

        list_response = self.client.get(f'/api/task-points/?mission_id={mission_id}&status=pending')
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()['data']['count'], 1)

        patch_response = self.client.patch(
            f'/api/task-points/{task_id}/',
            data=json.dumps({'priority': 9, 'status': 'assigned'}),
            content_type='application/json',
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()['data']['priority'], 9)

    def test_disaster_category_catalog(self):
        response = self.client.get('/api/disaster-categories/')
        self.assertEqual(response.status_code, 200)
        values = {item['value'] for item in response.json()['data']['items']}
        self.assertIn('flooded_road', values)
        self.assertIn('water', values)

    def test_image_upload_creates_mission(self):
        image = SimpleUploadedFile(
            'aerial.jpg',
            b'fake-jpeg-content',
            content_type='image/jpeg',
        )
        with override_settings(MEDIA_ROOT=self.media_root):
            response = self.client.post('/api/images/upload/', {'image': image})
            body = response.json()['data']
            media_response = self.client.get(f"/media/{body['image']['path']}")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(media_response.status_code, 200)
        self.assertEqual(b''.join(media_response.streaming_content), b'fake-jpeg-content')
        self.assertEqual(body['mission']['status'], 'created')
        self.assertTrue(body['image']['path'].startswith('missions/'))
        self.assertTrue(Path(body['image']['path']).name.endswith('.jpg'))
        self.assertTrue(Mission.objects.filter(pk=body['mission_id']).exists())

    def test_simulation_run_lifecycle(self):
        mission = Mission.objects.create(
            name='仿真测试任务',
            input_image_path='missions/simulation.jpg',
        )
        create_response = self.client.post(
            '/api/simulation-runs/',
            data=json.dumps({
                'mission_id': mission.pk,
                'planning_method': 'risk_aware_pso',
                'status': 'running',
                'uav_configuration': [{'identifier': 'UAV-01', 'battery_level': 82}],
                'task_snapshot': [{'id': 'T-001', 'priority': '高'}],
            }),
            content_type='application/json',
        )
        self.assertEqual(create_response.status_code, 201)
        run_id = create_response.json()['data']['id']
        run = SimulationRun.objects.get(pk=run_id)
        self.assertEqual(run.status, SimulationRun.Status.RUNNING)
        self.assertIsNotNone(run.started_at)

        update_response = self.client.patch(
            f'/api/simulation-runs/?simulation_id={run_id}',
            data=json.dumps({
                'status': 'completed',
                'summary_metrics': {'completion_rate': 1},
            }),
            content_type='application/json',
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()['data']['status'], 'completed')
        self.assertIsNotNone(SimulationRun.objects.get(pk=run_id).finished_at)


class RegionApiTests(CoreApiTests):
    """验证 palette mask 的缩放、连通域和空区域响应。"""

    def _write_mask(self, name, pixels):
        path = self.media_root / 'missions' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        mask = Image.new('P', (20, 10), 0)
        mask.putpalette([value for index in range(256) for value in (index, index, index)])
        data = mask.load()
        for (x, y), class_id in pixels.items():
            data[x, y] = class_id
        mask.save(path)
        return f'missions/{name}'

    def test_regions_keep_pixel_bounds_and_categories(self):
        pixels = {(x, y): 1 for x in range(3, 8) for y in range(2, 6)}
        pixels.update({(x, y): 3 for x in range(14, 19) for y in range(7, 9)})
        mission = Mission.objects.create(
            name='区域提取测试',
            input_image_path='missions/input.png',
            mask_path=self._write_mask('regions.png', pixels),
            image_width=20,
            image_height=10,
            inference_summary={
                'class_stats': [
                    {'id': 1, 'confidence': 0.91},
                    {'id': 3, 'confidence': 0.83},
                ],
                'mean_confidence': 0.8,
            },
        )
        with override_settings(MEDIA_ROOT=self.media_root):
            response = self.client.post(
                f'/api/missions/{mission.pk}/regions/',
                data=json.dumps({'min_area_px': 1, 'max_regions': 12}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()['data']
        self.assertEqual((body['width'], body['height']), (20, 10))
        self.assertEqual(len(body['regions']), 2)
        self.assertEqual({item['category'] for item in body['regions']}, {'flooded_building', 'flooded_road'})
        for item in body['regions']:
            self.assertGreaterEqual(item['x'], 0)
            self.assertLessEqual(item['x'], 20)
            self.assertGreaterEqual(item['y'], 0)
            self.assertLessEqual(item['y'], 10)
            x1, y1, x2, y2 = item['bbox']
            self.assertGreaterEqual(x1, 0)
            self.assertGreaterEqual(y1, 0)
            self.assertLessEqual(x2, 20)
            self.assertLessEqual(y2, 10)
            self.assertLessEqual(x1, x2)
            self.assertLessEqual(y1, y2)

    def test_empty_mask_returns_note_without_error(self):
        mission = Mission.objects.create(
            name='空区域测试',
            input_image_path='missions/input.png',
            mask_path=self._write_mask('empty.png', {}),
            image_width=20,
            image_height=10,
        )
        with override_settings(MEDIA_ROOT=self.media_root):
            response = self.client.post(
                f'/api/missions/{mission.pk}/regions/',
                data=json.dumps({}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()['data']
        self.assertEqual(body['regions'], [])
        self.assertEqual(body['note'], '未检出受淹区域')

    def test_large_4000_by_3000_mask_uses_image_coordinates(self):
        path = self.media_root / 'missions' / 'large.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        mask = Image.new('P', (4000, 3000), 0)
        mask.putpalette([value for index in range(256) for value in (index, index, index)])
        data = mask.load()
        for x in range(1000, 1800):
            for y in range(600, 1200):
                data[x, y] = 1
        mask.save(path)
        mission = Mission.objects.create(
            name='大图区域测试',
            input_image_path='missions/input.png',
            mask_path='missions/large.png',
            image_width=4000,
            image_height=3000,
            inference_summary={'class_stats': [{'id': 1, 'confidence': 0.88}]},
        )
        with override_settings(MEDIA_ROOT=self.media_root):
            response = self.client.post(
                f'/api/missions/{mission.pk}/regions/',
                data=json.dumps({'min_area_px': 2000, 'max_regions': 12}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()['data']
        self.assertEqual((body['width'], body['height']), (4000, 3000))
        self.assertEqual(len(body['regions']), 1)
        region = body['regions'][0]
        self.assertTrue(0 <= region['x'] <= 4000)
        self.assertTrue(0 <= region['y'] <= 3000)
        self.assertTrue(0 <= region['bbox'][0] <= region['bbox'][2] <= 4000)
        self.assertTrue(0 <= region['bbox'][1] <= region['bbox'][3] <= 3000)


class DispatchApiTests(RegionApiTests):
    """验证区域到任务点再到 planner 的完整编排和坐标还原。"""

    def test_dispatch_creates_tasks_and_restores_pixel_routes(self):
        pixels = {(x, y): 1 for x in range(3, 8) for y in range(2, 6)}
        pixels.update({(x, y): 3 for x in range(14, 19) for y in range(7, 9)})
        mission = Mission.objects.create(
            name='编排测试',
            input_image_path='missions/input.png',
            mask_path=self._write_mask('dispatch.png', pixels),
            image_width=20,
            image_height=10,
            inference_summary={'class_stats': [{'id': 1, 'confidence': 0.9}, {'id': 3, 'confidence': 0.8}]},
        )
        payload = {
            'min_area_px': 1,
            'max_regions': 12,
            'coordinate_scale': 0.1,
            'algorithm': 'round_robin',
            'uav_configuration': [{
                'id': 'UAV-01',
                'x': 10,
                'y': 9,
                'home': {'x': 10, 'y': 9},
                'battery_level': 100,
                'status': 'idle',
            }],
            'map_state': {'width': 20, 'height': 10, 'home': {'x': 10, 'y': 9}},
        }
        with override_settings(MEDIA_ROOT=self.media_root):
            response = self.client.post(
                f'/api/missions/{mission.pk}/dispatch/',
                data=json.dumps(payload),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 201)
        body = response.json()['data']
        self.assertEqual(len(body['regions']), 2)
        self.assertEqual(len(body['tasks']), 2)
        self.assertIsNotNone(body['plan'])
        self.assertEqual(body['plan']['config']['coordinate_scale'], 0.1)
        for route in body['plan']['routes'].values():
            for point in [route['start'], route['return'], *(route['tasks'] or [])]:
                if point:
                    self.assertGreaterEqual(point['x'], 0)
                    self.assertLessEqual(point['x'], 20)
                    self.assertGreaterEqual(point['y'], 0)
                    self.assertLessEqual(point['y'], 10)
        self.assertEqual(TaskPoint.objects.filter(mission=mission).count(), 2)

    def test_replan_restores_pixel_routes_after_failure(self):
        mission = Mission.objects.create(
            name='重规划测试',
            input_image_path='missions/input.png',
            image_width=100,
            image_height=60,
        )
        run = SimulationRun.objects.create(
            mission=mission,
            planning_method='risk_aware_pso',
            status=SimulationRun.Status.RUNNING,
            uav_configuration=[
                {'id': 'UAV-01', 'x': 50, 'y': 55, 'battery_level': 90, 'status': 'idle'},
                {'id': 'UAV-02', 'x': 58, 'y': 55, 'battery_level': 90, 'status': 'idle'},
            ],
            task_snapshot=[
                {'id': 'T-1', 'x': 20, 'y': 20, 'category': 'flooded_building', 'area': 20, 'confidence': 0.8, 'priority': 20, 'status': 'pending'},
                {'id': 'T-2', 'x': 80, 'y': 25, 'category': 'flooded_road', 'area': 20, 'confidence': 0.8, 'priority': 20, 'status': 'pending'},
            ],
            summary_metrics={
                'map_state': {'width': 100, 'height': 60, 'home': {'x': 50, 'y': 55}},
                'coordinate_scale': 0.1,
                'routes': {},
            },
        )
        response = self.client.post(
            f'/api/simulation-runs/{run.pk}/replan/',
            data=json.dumps({'event_type': 'uav_failure', 'uav_id': 'UAV-02'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        plan = response.json()['data']
        self.assertEqual(plan['config']['coordinate_scale'], 0.1)
        self.assertNotIn('UAV-02', plan['assignments'])
        for route in plan['routes'].values():
            self.assertGreaterEqual(route['start']['x'], 0)
            self.assertLessEqual(route['start']['x'], 100)
            self.assertGreaterEqual(route['start']['y'], 0)
            self.assertLessEqual(route['start']['y'], 60)

    def test_replan_and_finish_use_remaining_battery(self):
        mission = Mission.objects.create(name='电量仿真', input_image_path='missions/input.png')
        run = SimulationRun.objects.create(
            mission=mission,
            planning_method='risk_aware_pso',
            status=SimulationRun.Status.RUNNING,
            uav_configuration=[
                {'identifier': 'UAV-01', 'position_x': 10, 'position_y': 20,
                 'battery_level': 90, 'battery_reserve': 15, 'speed': 12},
                {'id': 'UAV-02', 'x': 10, 'y': 20, 'battery_level': 90},
            ],
            task_snapshot=[
                {'id': 'T-1', 'x': 20, 'y': 20, 'status': 'pending'},
                {'id': 'T-2', 'x': 40, 'y': 20, 'status': 'pending'},
            ],
            summary_metrics={
                'map_state': {'width': 100, 'height': 60, 'home': {'x': 10, 'y': 20}},
                'coordinate_scale': 0.1,
                'planner': {'config': {'energy_per_distance': 0.3}},
            },
        )
        response = self.client.post(
            f'/api/simulation-runs/{run.pk}/replan/',
            {
                'event_type': 'uav_failure',
                'uav_id': 'UAV-02',
                'current_state': {
                    'uavs': [
                        {'id': 'UAV-01', 'x': 20, 'y': 20, 'battery_level': 80},
                        {'id': 'UAV-02', 'x': 15, 'y': 20, 'battery_level': 76},
                    ],
                    'completed_task_ids': ['T-1'],
                },
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        plan = response.json()['data']
        self.assertEqual(plan['assignments'], {'UAV-01': ['T-2']})
        route = plan['routes']['UAV-01']
        self.assertEqual(route['start'], {'x': 20, 'y': 20})
        self.assertEqual(route['return'], {'x': 10, 'y': 20})
        self.assertAlmostEqual(route['energy'], 1.5)
        self.assertEqual(route['battery_reserve'], 15)

        finish_url = f'/api/simulation-runs/?simulation_id={run.pk}'
        finish_state = {
            'uavs': [{'id': 'UAV-01', 'x': 10, 'y': 20, 'battery_level': 78.5}],
            'completed_task_ids': ['T-2'],
        }
        response = self.client.patch(
            finish_url, {'status': 'completed', 'current_state': finish_state}, content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        run.refresh_from_db()
        self.assertEqual(run.status, 'completed')
        active, failed = run.uav_configuration
        self.assertEqual((active['battery_level'], active['position_x'], active['speed']), (78.5, 10, 12))
        self.assertEqual((failed['battery_level'], failed['status']), (76, 'failed'))
        self.assertEqual([task['status'] for task in run.task_snapshot], ['completed', 'completed'])

        finish_state['uavs'][0]['battery_level'] = 90
        response = self.client.patch(finish_url, {'current_state': finish_state}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        run.refresh_from_db()
        self.assertEqual(run.uav_configuration[0]['battery_level'], 78.5)

# Create your tests here.
