from dataclasses import dataclass
from typing import List, Tuple

TRACK_LENGTH = 260.0


@dataclass(frozen=True)
class Obstacle:
    x: float
    y_offset: float
    z: float
    hx: float
    hy: float
    hz: float
    color: Tuple[float, float, float]


@dataclass(frozen=True)
class RoadSegment:
    ax: float
    az: float
    bx: float
    bz: float
    half_width: float


# 多条有夹角的道路（主路 + 两条斜向连接路）
ROAD_SEGMENTS: List[RoadSegment] = [
    RoadSegment(0.0, 0.0, 0.0, 260.0, 7.5),            # 主干道
    RoadSegment(-20.0, 60.0, 18.0, 120.0, 5.2),        # 左下->右上斜道
    RoadSegment(18.0, 130.0, -22.0, 210.0, 5.0),       # 右下->左上斜道
    RoadSegment(-24.0, 170.0, -8.0, 250.0, 4.8),       # 外侧支路
]

OBSTACLES = [
    Obstacle(-4.0, 0.9, 40.0, 0.8, 0.9, 2.8, (0.8, 0.3, 0.2)),
    Obstacle(3.6, 0.9, 82.0, 0.8, 0.9, 2.8, (0.2, 0.6, 0.9)),
    Obstacle(0.0, 1.1, 140.0, 1.1, 1.1, 4.2, (0.92, 0.45, 0.2)),
    Obstacle(-6.0, 0.8, 188.0, 0.9, 0.8, 2.2, (0.18, 0.65, 0.75)),
    Obstacle(5.8, 0.8, 220.0, 0.9, 0.8, 2.2, (0.75, 0.3, 0.85)),
]


def ground_height(z: float) -> float:
    if z < 40.0:
        return 0.0
    if z < 80.0:
        return (z - 40.0) * 0.16
    if z < 130.0:
        return 6.4
    if z < 170.0:
        return 6.4 - (z - 130.0) * 0.16
    if z < 210.0:
        return (z - 170.0) * 0.12
    return max(0.0, 4.8 - (z - 210.0) * 0.12)


def slope_dz(z: float) -> float:
    if 40.0 <= z < 80.0:
        return 0.16
    if 130.0 <= z < 170.0:
        return -0.16
    if 170.0 <= z < 210.0:
        return 0.12
    if 210.0 <= z < 250.0:
        return -0.12
    return 0.0
