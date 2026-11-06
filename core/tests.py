import json
import shutil
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import TestCase, override_settings

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

# Create your tests here.

