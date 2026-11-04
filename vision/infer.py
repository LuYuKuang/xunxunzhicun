"""FloodNet 单例推理引擎。

该模块不在 Django 导入时加载 torch 或权重，首次调用时才加载一次，并自动回退到 CPU。
"""

from __future__ import annotations

import os
import time
from pathlib import Path


CLASS_NAMES = [
    '背景', '受淹建筑', '非受淹建筑', '受淹道路', '非受淹道路',
    '水体', '树木', '车辆', '水池', '草地',
]
CLASS_COLORS = [
    (0, 0, 0), (239, 141, 115), (180, 180, 180), (228, 188, 112),
    (150, 150, 150), (120, 213, 197), (112, 166, 116), (155, 156, 248),
    (91, 166, 222), (154, 178, 103),
]


class ModelUnavailable(RuntimeError):
    """视觉依赖或模型权重尚未就绪。"""


class FloodNetInferenceEngine:
    def __init__(self, weight_path: str | None = None, input_size: int = 512):
        self.weight_path = weight_path or os.environ.get('FLOODNET_MODEL_PATH', 'floodnet_deeplabv3.pt')
        self.input_size = int(input_size)
        self._model = None
        self._torch = None
        self._device = None
        self._num_classes = len(CLASS_NAMES)

    def _resolve_weight_path(self):
        try:
            from django.conf import settings

            model_dir = Path(os.environ.get('MODEL_DIR', str(settings.BASE_DIR / 'vision' / 'weights')))
        except Exception:
            model_dir = Path(os.environ.get('MODEL_DIR', 'vision/weights'))
        path = Path(self.weight_path)
        if path.is_absolute():
            return path
        candidates = [model_dir / path]
        try:
            from django.conf import settings
            candidates.append(Path(settings.BASE_DIR) / path)
        except Exception:
            pass
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _load(self):
        if self._model is not None:
            return
        try:
            import torch
        except ImportError as exc:
            raise ModelUnavailable('未安装 torch/torchvision，请先安装 requirements-vision.txt。') from exc

        weight_path = self._resolve_weight_path()
        if not weight_path.exists():
            raise ModelUnavailable(f'模型权重不存在：{weight_path.as_posix()}。请先完成训练并放入 vision/weights。')
        try:
            from .models import build_model
            checkpoint = torch.load(weight_path, map_location='cpu')
            if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
                self._num_classes = int(checkpoint.get('num_classes', self._num_classes))
                self.input_size = int(checkpoint.get('input_size', self.input_size))
            else:
                state_dict = checkpoint
            if isinstance(state_dict, dict) and state_dict and all(key.startswith('module.') for key in state_dict):
                state_dict = {key[7:]: value for key, value in state_dict.items()}
            model = build_model(num_classes=self._num_classes, pretrained=False)
            model.load_state_dict(state_dict)
            self._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self._model = model.to(self._device).eval()
            self._torch = torch
        except Exception as exc:
            raise ModelUnavailable(f'加载模型失败：{exc}') from exc

    def predict(self, image_file):
        """返回 mask PNG 字节、类别统计和供任务模块使用的区域摘要。"""
        self._load()
        from PIL import Image
        from torchvision.transforms import functional as TF
        import io

        image = Image.open(image_file).convert('RGB')
        original_size = image.size
        resized = image.resize((self.input_size, self.input_size), Image.Resampling.BILINEAR)
        tensor = TF.to_tensor(resized)
        tensor = TF.normalize(tensor, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]).unsqueeze(0)

        started = time.perf_counter()
        with self._torch.inference_mode():
            output = self._model(tensor.to(self._device))['out'][0]
            probabilities = output.softmax(dim=0)
            labels = probabilities.argmax(dim=0).to('cpu')
            confidence = probabilities.max(dim=0).values.to('cpu')
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

        # 使用 PIL 的最近邻缩放，避免类别 ID 被插值破坏。
        label_image = Image.fromarray(labels.numpy().astype('uint8'), mode='L')
        label_image = label_image.resize(original_size, Image.Resampling.NEAREST)
        label_values = self._torch.as_tensor(list(label_image.getdata()), dtype=self._torch.long)
        total = max(1, label_values.numel())
        class_stats = []
        for class_id, class_name in enumerate(CLASS_NAMES[:self._num_classes]):
            count = int((label_values == class_id).sum().item())
            class_confidence_values = confidence[labels == class_id]
            class_confidence = float(class_confidence_values.mean().item()) if class_confidence_values.numel() else 0.0
            class_stats.append({
                'id': class_id,
                'label': class_name,
                'pixels': count,
                'ratio': round(count / total, 6),
                'confidence': round(class_confidence, 6),
            })

        # 严格的淹水占比只合并 flooded building/road；自然水体保留为独立类别。
        flood_ids = {1, 3}
        flood_pixels = sum(item['pixels'] for item in class_stats if item['id'] in flood_ids)
        avg_confidence = round(float(confidence.mean().item()), 6)
        color_mask = label_image.convert('P')
        color_mask.putpalette(sum((list(color) for color in CLASS_COLORS), []) + [0] * (768 - len(CLASS_COLORS) * 3))
        mask_buffer = io.BytesIO()
        color_mask.save(mask_buffer, format='PNG')
        return {
            'mask_bytes': mask_buffer.getvalue(),
            'width': original_size[0],
            'height': original_size[1],
            'class_stats': class_stats,
            'flood_ratio': round(flood_pixels / total, 6),
            'mean_confidence': avg_confidence,
            'inference_ms': elapsed_ms,
            'device': str(self._device),
            'model_classes': self._num_classes,
        }


_ENGINE = None


def get_engine(weight_path=None):
    """进程级单例；同一 Web 进程不会为每次请求重复加载权重。"""
    global _ENGINE
    if _ENGINE is None or weight_path:
        _ENGINE = FloodNetInferenceEngine(weight_path=weight_path)
    return _ENGINE


