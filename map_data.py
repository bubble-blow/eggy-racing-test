from dataclasses import dataclass
from typing import Tuple

TRACK_HALF_WIDTH = 9.0
TRACK_LENGTH = 220.0


@dataclass(frozen=True)
class Obstacle:
    x: float
    y_offset: float
    z: float
    hx: float
    hy: float
    hz: float
    color: Tuple[float, float, float]


# 通过障碍布局形成多条可选路径（中路、左路、右路）
OBSTACLES = [
    Obstacle(0.0, 0.9, 40.0, 0.9, 0.9, 3.2, (0.8, 0.3, 0.2)),
    Obstacle(-3.2, 0.9, 58.0, 0.9, 0.9, 3.0, (0.2, 0.6, 0.9)),
    Obstacle(3.2, 0.9, 76.0, 0.9, 0.9, 3.0, (0.2, 0.6, 0.9)),
    Obstacle(0.0, 1.1, 96.0, 1.2, 1.1, 4.0, (0.92, 0.45, 0.2)),
    Obstacle(-5.2, 0.7, 116.0, 1.0, 0.7, 2.0, (0.75, 0.3, 0.85)),
    Obstacle(5.2, 0.7, 116.0, 1.0, 0.7, 2.0, (0.75, 0.3, 0.85)),
    Obstacle(-2.2, 0.8, 142.0, 0.8, 0.8, 3.4, (0.18, 0.65, 0.75)),
    Obstacle(2.2, 0.8, 142.0, 0.8, 0.8, 3.4, (0.18, 0.65, 0.75)),
    Obstacle(0.0, 1.0, 168.0, 1.0, 1.0, 5.0, (0.9, 0.2, 0.35)),
    Obstacle(-4.0, 0.9, 192.0, 0.8, 0.9, 2.5, (0.2, 0.75, 0.45)),
    Obstacle(4.0, 0.9, 204.0, 0.8, 0.9, 2.5, (0.2, 0.75, 0.45)),
]


def track_half_width(z: float) -> float:
    if z < 50.0:
        return 9.0
    if z < 120.0:
        return 11.0
    if z < 180.0:
        return 8.0
    return 10.0


def ground_height(z: float) -> float:
    # 平地 -> 上坡 -> 高台 -> 下坡 -> 平地 -> 大上坡 -> 高台 -> 下坡
    if z < 30.0:
        return 0.0
    if z < 60.0:
        return (z - 30.0) * 0.2
    if z < 90.0:
        return 6.0
    if z < 120.0:
        return 6.0 - (z - 90.0) * 0.2
    if z < 150.0:
        return 0.0
    if z < 180.0:
        return (z - 150.0) * 0.25
    if z < 205.0:
        return 7.5
    if z < 220.0:
        return 7.5 - (z - 205.0) * 0.5
    return 0.0


def slope_dz(z: float) -> float:
    if 30.0 <= z < 60.0:
        return 0.2
    if 90.0 <= z < 120.0:
        return -0.2
    if 150.0 <= z < 180.0:
        return 0.25
    if 205.0 <= z < 220.0:
        return -0.5
    return 0.0
