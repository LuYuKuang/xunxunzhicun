"""任务生成输入结构。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    x: float
    y: float
    category: str
    area: float
    confidence: float
    uncertainty: float


