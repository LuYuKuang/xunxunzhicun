"""从 FloodNet 调色板 mask 提取受淹区域及像素坐标。"""

from __future__ import annotations

import math
from collections import deque

from django.core.files.storage import default_storage
from PIL import Image


FLOOD_CLASSES = {
    1: 'flooded_building',
    3: 'flooded_road',
}
MAX_LONG_SIDE = 512


def _component_pixels(labels, width, height, class_id):
    """在降采样后的类别索引上找连通域。"""
    visited = bytearray(width * height)
    components = []
    for y in range(height):
        for x in range(width):
            index = y * width + x
            if visited[index] or labels[index] != class_id:
                continue
            visited[index] = 1
            queue = deque([index])
            points = []
            while queue:
                current = queue.popleft()
                current_y, current_x = divmod(current, width)
                points.append((current_x, current_y))
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if not (0 <= next_x < width and 0 <= next_y < height):
                        continue
                    next_index = next_y * width + next_x
                    if visited[next_index] or labels[next_index] != class_id:
                        continue
                    visited[next_index] = 1
                    queue.append(next_index)
            components.append(points)
    return components


def _class_confidence(summary, class_id):
    for item in (summary or {}).get('class_stats') or []:
        if int(item.get('id', -1)) == class_id:
            return float(item.get('confidence') or 0.0)
    return float((summary or {}).get('mean_confidence') or 0.0)


def extract_flood_regions(mission, min_area_px=2000, max_regions=12):
    """读取 Mission mask，返回原图像素坐标系中的受淹区域。"""
    min_area_px = max(0.0, float(min_area_px))
    max_regions = max(1, min(100, int(max_regions)))
    stored_width = int(mission.image_width or 0)
    stored_height = int(mission.image_height or 0)
    if not mission.mask_path:
        return {
            'width': stored_width,
            'height': stored_height,
            'regions': [],
            'note': '未检出受淹区域',
        }

    with default_storage.open(mission.mask_path, 'rb') as handle:
        mask = Image.open(handle)
        mask.load()
        if mask.mode != 'P':
            mask = mask.convert('P')
        source_width, source_height = mask.size
        width = stored_width or source_width
        height = stored_height or source_height
        if width <= 0 or height <= 0:
            width, height = source_width, source_height
        long_side = max(source_width, source_height)
        resize_ratio = min(1.0, MAX_LONG_SIDE / long_side) if long_side else 1.0
        small_width = max(1, int(round(source_width * resize_ratio)))
        small_height = max(1, int(round(source_height * resize_ratio)))
        reduced = mask.resize((small_width, small_height), Image.Resampling.NEAREST)
        labels = list(reduced.getdata())

    scale_x = width / small_width
    scale_y = height / small_height
    candidates = []
    for class_id, category in FLOOD_CLASSES.items():
        confidence = _class_confidence(mission.inference_summary, class_id)
        for points in _component_pixels(labels, small_width, small_height, class_id):
            if not points:
                continue
            area_px = len(points) * scale_x * scale_y
            if area_px < min_area_px:
                continue
            min_x = min(point[0] for point in points)
            max_x = max(point[0] for point in points)
            min_y = min(point[1] for point in points)
            max_y = max(point[1] for point in points)
            centroid_x = sum((point[0] + 0.5) * scale_x for point in points) / len(points)
            centroid_y = sum((point[1] + 0.5) * scale_y for point in points) / len(points)
            x1 = max(0, min(width, int(math.floor(min_x * scale_x))))
            y1 = max(0, min(height, int(math.floor(min_y * scale_y))))
            x2 = max(x1, min(width, int(math.ceil((max_x + 1) * scale_x))))
            y2 = max(y1, min(height, int(math.ceil((max_y + 1) * scale_y))))
            candidates.append({
                'x': max(0, min(width, int(round(centroid_x)))),
                'y': max(0, min(height, int(round(centroid_y)))),
                'bbox': [x1, y1, x2, y2],
                'category': category,
                'area_px': round(area_px, 2),
                'area_ratio': round(area_px / max(1, width * height), 8),
                'confidence': round(max(0.0, min(1.0, confidence)), 6),
            })

    candidates.sort(key=lambda item: item['area_px'], reverse=True)
    regions = []
    for index, item in enumerate(candidates[:max_regions], start=1):
        regions.append({'id': f'R-{index:03d}', **item})
    return {
        'width': width,
        'height': height,
        'regions': regions,
        'note': '' if regions else '未检出受淹区域',
    }


