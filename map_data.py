from dataclasses import dataclass

TRACK_HALF_WIDTH = 5.0
TRACK_LENGTH = 120.0


@dataclass(frozen=True)
class Obstacle:
    x: float
    y_offset: float
    z: float
    hx: float
    hy: float
    hz: float
    color: tuple[float, float, float]


OBSTACLES = [
    Obstacle(1.8, 0.8, 36.0, 0.9, 0.8, 0.9, (0.2, 0.35, 0.9)),
    Obstacle(-1.5, 0.8, 74.0, 1.2, 0.8, 1.0, (0.75, 0.3, 0.85)),
    Obstacle(0.0, 1.0, 52.0, 0.7, 1.0, 0.7, (0.92, 0.45, 0.2)),
    Obstacle(2.8, 0.6, 92.0, 0.8, 0.6, 1.5, (0.18, 0.65, 0.75)),
    Obstacle(-2.8, 0.6, 102.0, 0.8, 0.6, 1.5, (0.18, 0.65, 0.75)),
]


def ground_height(z: float) -> float:
    # 平地 -> 斜坡上升 -> 平台 -> 斜坡下降
    if z < 26.0:
        return 0.0
    if z < 46.0:
        return (z - 26.0) * 0.28
    if z < 66.0:
        return 5.6
    if z < 86.0:
        return 5.6 - (z - 66.0) * 0.28
    return 0.0


def slope_dz(z: float) -> float:
    if 26.0 <= z < 46.0:
        return 0.28
    if 66.0 <= z < 86.0:
        return -0.28
    return 0.0
