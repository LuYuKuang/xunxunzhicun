"""可解释的复查任务优先级。"""

SEVERITY = {
    'flooded_building': 3.0,
    'flooded_road': 3.0,
    'flooded_area': 2.0,
    'water': 1.5,
}


def calculate_priority(category, area, confidence, uncertainty=None):
    uncertainty = max(0.0, min(1.0, 1.0 - float(confidence) if uncertainty is None else float(uncertainty)))
    return max(1, round(SEVERITY.get(category, 1.0) * max(float(area), 1.0) * max(uncertainty, 0.05) * 100))


