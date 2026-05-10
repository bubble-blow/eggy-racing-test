import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TERRAIN_PATH = Path("data/terrain.json")
Mode = str


@dataclass
class Cell:
    mode: Mode
    corners: list[float]  # [h00, h10, h11, h01]


@dataclass
class Terrain:
    width: int
    height: int
    cells: list[list[Cell]]

    def save(self, path: Path = TERRAIN_PATH) -> None:
        payload = {
            "width": self.width,
            "height": self.height,
            "cells": [
                [
                    {"mode": c.mode, "corners": c.corners}
                    for c in row
                ]
                for row in self.cells
            ],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = TERRAIN_PATH) -> "Terrain":
        if not path.exists():
            return cls.create_default(20, 20)
        payload = json.loads(path.read_text(encoding="utf-8"))

        # New format: per-cell records with mode+corners
        first = payload["cells"][0][0]
        if isinstance(first, dict) and "corners" in first:
            cells = [
                [Cell(mode=item.get("mode", "fixed"), corners=[float(v) for v in item["corners"]]) for item in row]
                for row in payload["cells"]
            ]
            return cls(payload["width"], payload["height"], cells)

        # Legacy format migration: vertex height grid -> decoupled cells
        legacy = np.array(payload["cells"], dtype=np.float32)
        h, w = legacy.shape
        cell_w = max(1, w - 1)
        cell_h = max(1, h - 1)
        cells = []
        for y in range(cell_h):
            row = []
            for x in range(cell_w):
                corners = [
                    float(legacy[y, x]),
                    float(legacy[y, x + 1]),
                    float(legacy[y + 1, x + 1]),
                    float(legacy[y + 1, x]),
                ]
                row.append(Cell(mode="fixed", corners=corners))
            cells.append(row)
        return cls(cell_w, cell_h, cells)

    @classmethod
    def create_default(cls, width: int, height: int) -> "Terrain":
        cells = [[Cell(mode="fixed", corners=[0.0, 0.0, 0.0, 0.0]) for _ in range(width)] for _ in range(height)]
        return cls(width, height, cells)

    def set_cell_height(self, cell_x: int, cell_y: int, value: float, mode: Mode) -> None:
        if not (0 <= cell_x < self.width and 0 <= cell_y < self.height):
            return
        self.cells[cell_y][cell_x].mode = mode
        self.cells[cell_y][cell_x].corners = [float(value)] * 4

    def _effective_corners(self, x: int, y: int) -> list[float]:
        cell = self.cells[y][x]
        if cell.mode != "adaptive":
            return cell.corners

        c = cell.corners[:]

        # Adaptive mode: edge/corner blending with neighbors (only for this cell)
        if y > 0:
            top = self.cells[y - 1][x].corners
            c[0] = (c[0] + top[3]) * 0.5
            c[1] = (c[1] + top[2]) * 0.5
        if y < self.height - 1:
            bottom = self.cells[y + 1][x].corners
            c[3] = (c[3] + bottom[0]) * 0.5
            c[2] = (c[2] + bottom[1]) * 0.5
        if x > 0:
            left = self.cells[y][x - 1].corners
            c[0] = (c[0] + left[1]) * 0.5
            c[3] = (c[3] + left[2]) * 0.5
        if x < self.width - 1:
            right = self.cells[y][x + 1].corners
            c[1] = (c[1] + right[0]) * 0.5
            c[2] = (c[2] + right[3]) * 0.5
        return c

    def sample_height(self, world_x: float, world_z: float) -> float:
        gx = np.clip(world_x + self.width / 2, 0, self.width - 1e-4)
        gy = np.clip(world_z + self.height / 2, 0, self.height - 1e-4)
        cx, cy = int(np.floor(gx)), int(np.floor(gy))
        tx, ty = gx - cx, gy - cy
        h00, h10, h11, h01 = self._effective_corners(cx, cy)
        return float((h00 * (1 - tx) + h10 * tx) * (1 - ty) + (h01 * (1 - tx) + h11 * tx) * ty)


def draw_terrain(terrain: Terrain, wireframe: bool = False) -> None:
    from OpenGL.GL import GL_FILL, GL_FRONT_AND_BACK, GL_LINE, GL_QUADS, glBegin, glColor3f, glEnd, glPolygonMode, glVertex3f

    glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if wireframe else GL_FILL)
    for y in range(terrain.height):
        for x in range(terrain.width):
            wx = x - terrain.width / 2
            wz = y - terrain.height / 2
            h00, h10, h11, h01 = terrain._effective_corners(x, y)
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
