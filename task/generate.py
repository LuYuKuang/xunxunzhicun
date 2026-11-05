"""将模型输出区域转换成可供 planner 使用的任务字典。"""

from .priority import calculate_priority


def regions_to_tasks(regions):
    items = []
    for index, region in enumerate(regions or [], start=1):
        category = str(region.get('disaster_category', region.get('category', 'flooded_area')))
        area = max(0.0, float(region.get('area', 0.0) or 0.0))
        confidence = max(0.0, min(1.0, float(region.get('confidence', 0.0) or 0.0)))
        uncertainty = max(0.0, min(1.0, float(region.get('uncertainty', 1.0 - confidence) or 0.0)))
        items.append({
            'id': str(region.get('id', f'R-{index:03d}')),
            'x': float(region.get('coordinate_x', region.get('x', 0.0)) or 0.0),
            'y': float(region.get('coordinate_y', region.get('y', 0.0)) or 0.0),
            'category': category,
            'area': area,
            'confidence': confidence,
            'uncertainty': uncertainty,
            'priority': calculate_priority(category, area, confidence, uncertainty),
            'service_time': float(region.get('service_time', 1.0) or 1.0),
            'deadline': region.get('deadline'),
            'status': 'pending',
        })
    return items


