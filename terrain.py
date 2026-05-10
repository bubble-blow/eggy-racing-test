import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TERRAIN_PATH = Path("data/terrain.json")

Mode = str


@dataclass
class Terrain:
    heights: np.ndarray

    @property
    def width(self) -> int:
        return int(self.heights.shape[1])

    @property
    def height(self) -> int:
        return int(self.heights.shape[0])

    def save(self, path: Path = TERRAIN_PATH) -> None:
        payload = {
            "width": self.width,
            "height": self.height,
            "cells": self.heights.tolist(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = TERRAIN_PATH) -> "Terrain":
        if not path.exists():
            return cls(np.zeros((20, 20), dtype=np.float32))
        payload = json.loads(path.read_text(encoding="utf-8"))
        arr = np.array(payload["cells"], dtype=np.float32)
        return cls(arr)

    def set_height(self, x: int, y: int, value: float, mode: Mode) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        self.heights[y, x] = value
        if mode == "adaptive":
            self._smooth_neighbors(x, y)


    def set_cell_height(self, cell_x: int, cell_y: int, value: float, mode: Mode) -> None:
        """Apply height to one full grid cell by updating its 4 corner vertices."""
        if not (0 <= cell_x < self.width - 1 and 0 <= cell_y < self.height - 1):
            return
        corners = [(cell_x, cell_y), (cell_x + 1, cell_y), (cell_x + 1, cell_y + 1), (cell_x, cell_y + 1)]
        for vx, vy in corners:
            self.heights[vy, vx] = value
            if mode == "adaptive":
                self._smooth_neighbors(vx, vy)

    def _smooth_neighbors(self, x: int, y: int) -> None:
        for ny in range(max(0, y - 1), min(self.height, y + 2)):
            for nx in range(max(0, x - 1), min(self.width, x + 2)):
                if nx == x and ny == y:
                    continue
                self.heights[ny, nx] = (self.heights[ny, nx] * 0.65) + (self.heights[y, x] * 0.35)

    def sample_height(self, world_x: float, world_z: float) -> float:
        gx = np.clip(world_x + self.width / 2, 0, self.width - 1)
        gy = np.clip(world_z + self.height / 2, 0, self.height - 1)
        x0, y0 = int(np.floor(gx)), int(np.floor(gy))
        x1, y1 = min(x0 + 1, self.width - 1), min(y0 + 1, self.height - 1)
        tx, ty = gx - x0, gy - y0
        h00 = self.heights[y0, x0]
        h10 = self.heights[y0, x1]
        h01 = self.heights[y1, x0]
        h11 = self.heights[y1, x1]
        return float((h00 * (1 - tx) + h10 * tx) * (1 - ty) + (h01 * (1 - tx) + h11 * tx) * ty)


def draw_terrain(terrain: Terrain, wireframe: bool = False) -> None:
    from OpenGL.GL import (
        GL_FILL,
        GL_FRONT_AND_BACK,
        GL_LINE,
        GL_QUADS,
        glBegin,
        glColor3f,
        glEnd,
        glPolygonMode,
        glVertex3f,
    )

    glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if wireframe else GL_FILL)
    for y in range(terrain.height - 1):
        for x in range(terrain.width - 1):
            wx = x - terrain.width / 2
            wz = y - terrain.height / 2
            h00 = terrain.heights[y, x]
            h10 = terrain.heights[y, x + 1]
            h11 = terrain.heights[y + 1, x + 1]
            h01 = terrain.heights[y + 1, x]
            if wireframe:
                glColor3f(0.9, 0.95, 1.0)
            else:
                shade = 0.3 + min(0.7, (h00 + h10 + h11 + h01) / 16.0)
                glColor3f(0.2, shade, 0.2)
            glBegin(GL_QUADS)
            glVertex3f(wx, h00, wz)
            glVertex3f(wx + 1, h10, wz)
            glVertex3f(wx + 1, h11, wz + 1)
            glVertex3f(wx, h01, wz + 1)
            glEnd()
