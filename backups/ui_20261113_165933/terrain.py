"""Seeded terrain classification and movement modifiers."""

from __future__ import annotations

import math
import random

# Speed multipliers by surface
TERRAIN = {
    "habitat": {"speed": 1.0, "friction": 1.0, "name": "Prepared pad"},
    "metal": {"speed": 1.08, "friction": 0.9, "name": "Metal floor"},
    "sand": {"speed": 0.72, "friction": 1.35, "name": "Soft sand"},
    "rocky": {"speed": 0.82, "friction": 1.15, "name": "Rocky ground"},
    "outer": {"speed": 0.9, "friction": 1.1, "name": "Outer terrain"},
}

CELL = 64


def build_terrain_map(colony: dict, seed: int = 42) -> dict:
    """
    Coarse cell map for fast lookups. Values are terrain keys.
    Decoration (sand patches, metal pads) are seeded and stable.
    """
    rng = random.Random(seed)
    ww, wh = colony["world_w"], colony["world_h"]
    cols = math.ceil(ww / CELL)
    rows = math.ceil(wh / CELL)
    grid = [["outer"] * cols for _ in range(rows)]

    def fill_rect(rect, kind):
        x0 = max(0, rect.x // CELL)
        y0 = max(0, rect.y // CELL)
        x1 = min(cols, (rect.right + CELL - 1) // CELL)
        y1 = min(rows, (rect.bottom + CELL - 1) // CELL)
        for ry in range(y0, y1):
            for cx in range(x0, x1):
                grid[ry][cx] = kind

    for zone in colony["zones"]:
        zid = zone["id"]
        if zid == "habitat":
            fill_rect(zone["rect"], "habitat")
        elif zid == "comm":
            fill_rect(zone["rect"], "rocky")
        elif zid == "energy":
            fill_rect(zone["rect"], "rocky")
        elif zid == "rover":
            fill_rect(zone["rect"], "metal")
        elif zid == "research":
            fill_rect(zone["rect"], "habitat")

    # Soft sand patches (outer + edges)
    for _ in range(48):
        cx = rng.randint(0, cols - 1)
        cy = rng.randint(0, rows - 1)
        if grid[cy][cx] == "outer" or rng.random() < 0.25:
            for oy in range(-1, 2):
                for ox in range(-1, 2):
                    x, y = cx + ox, cy + oy
                    if 0 <= x < cols and 0 <= y < rows and grid[y][x] in ("outer", "rocky"):
                        if rng.random() < 0.7:
                            grid[y][x] = "sand"

    # Metal pads near stations
    for st in colony["stations"]:
        cx = int(st["pos"][0] // CELL)
        cy = int(st["pos"][1] // CELL)
        for oy in range(-1, 2):
            for ox in range(-1, 2):
                x, y = cx + ox, cy + oy
                if 0 <= x < cols and 0 <= y < rows:
                    grid[y][x] = "metal"

    return {"cell": CELL, "cols": cols, "rows": rows, "grid": grid}


def terrain_at(tmap: dict, x: float, y: float) -> str:
    cx = int(x // tmap["cell"])
    cy = int(y // tmap["cell"])
    if cx < 0 or cy < 0 or cx >= tmap["cols"] or cy >= tmap["rows"]:
        return "outer"
    return tmap["grid"][cy][cx]


def terrain_props(tmap: dict, x: float, y: float) -> dict:
    key = terrain_at(tmap, x, y)
    return TERRAIN.get(key, TERRAIN["outer"])
