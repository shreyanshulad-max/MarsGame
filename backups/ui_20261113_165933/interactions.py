"""Data-driven interaction targets (stations + collectibles)."""

from __future__ import annotations

import math
from typing import Any, Optional


def nearest_interactable(astro: dict, items: list[dict], exclude_collected: bool = True) -> Optional[dict]:
    """Return nearest in-range interactable; stations win over collectibles if tied."""
    best = None
    best_d = 1e9
    best_pri = 99
    ax, ay = astro["x"], astro["y"]
    for it in items:
        if exclude_collected and it.get("collected"):
            continue
        if it.get("disabled"):
            continue
        d = math.hypot(ax - it["pos"][0], ay - it["pos"][1])
        if d > it.get("radius", 60):
            continue
        pri = 0 if it.get("type") == "station" else 1
        if d < best_d - 0.01 or (abs(d - best_d) < 0.01 and pri < best_pri):
            best = it
            best_d = d
            best_pri = pri
    return best


def make_station(
    uid: str,
    name: str,
    pos: tuple,
    screen: str,
    prompt: str,
    marker: tuple,
    radius: float = 72,
) -> dict[str, Any]:
    return {
        "id": uid,
        "name": name,
        "pos": (float(pos[0]), float(pos[1])),
        "radius": float(radius),
        "type": "station",
        "prompt": prompt,
        "description": prompt,
        "action": "open_challenge",
        "screen": screen,
        "marker": marker,
        "status": "ready",
        "collected": False,
        "disabled": False,
    }


def make_collectible(
    uid: str,
    name: str,
    pos: tuple,
    kind: str,
    prompt: str,
    marker: tuple = (180, 220, 120),
    radius: float = 56,
) -> dict[str, Any]:
    return {
        "id": uid,
        "name": name,
        "pos": (float(pos[0]), float(pos[1])),
        "radius": float(radius),
        "type": "collectible",
        "kind": kind,
        "prompt": prompt,
        "description": prompt,
        "action": "collect",
        "screen": None,
        "marker": marker,
        "status": "available",
        "collected": False,
        "disabled": False,
    }
