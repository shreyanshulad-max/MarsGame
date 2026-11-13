"""Smooth follow camera with optional micro-shake."""

from __future__ import annotations

import math
import random


def make_camera(astro, view_w: int, view_h: int) -> dict:
    return {
        "x": float(astro["x"] - view_w * 0.5),
        "y": float(astro["y"] - view_h * 0.55),
        "view_w": view_w,
        "view_h": view_h,
        "shake": 0.0,
        "shake_mag": 0.0,
        "ox": 0.0,
        "oy": 0.0,
    }


def clamp_camera(cam: dict, world_w: int, world_h: int) -> dict:
    max_x = max(0.0, float(world_w - cam["view_w"]))
    max_y = max(0.0, float(world_h - cam["view_h"]))
    cam["x"] = max(0.0, min(max_x, cam["x"]))
    cam["y"] = max(0.0, min(max_y, cam["y"]))
    return cam


def add_shake(cam: dict, amount: float = 0.18, mag: float = 3.5) -> None:
    cam["shake"] = max(cam.get("shake", 0.0), amount)
    cam["shake_mag"] = max(cam.get("shake_mag", 0.0), mag)


def update_camera(
    cam: dict,
    astro: dict,
    dt: float,
    world_w: int,
    world_h: int,
    lerp: float = 7.0,
) -> dict:
    target_x = astro["x"] - cam["view_w"] * 0.5
    target_y = astro["y"] - cam["view_h"] * 0.55
    t = min(1.0, lerp * max(dt, 0.0))
    cam["x"] += (target_x - cam["x"]) * t
    cam["y"] += (target_y - cam["y"]) * t

    if cam.get("shake", 0) > 0:
        cam["shake"] -= dt
        mag = cam.get("shake_mag", 3.0) * max(0.0, cam["shake"])
        cam["ox"] = random.uniform(-mag, mag)
        cam["oy"] = random.uniform(-mag, mag)
    else:
        cam["ox"] = cam["oy"] = 0.0
        cam["shake_mag"] = 0.0

    return clamp_camera(cam, world_w, world_h)


def render_offset(cam: dict) -> tuple[float, float]:
    """Camera origin used for world→screen (includes shake)."""
    return cam["x"] + cam.get("ox", 0.0), cam["y"] + cam.get("oy", 0.0)


def world_to_screen(wx: float, wy: float, cam: dict) -> tuple[int, int]:
    ox, oy = render_offset(cam)
    return int(wx - ox), int(wy - oy)


def screen_to_world(sx: float, sy: float, cam: dict) -> tuple[float, float]:
    ox, oy = render_offset(cam)
    return float(sx + ox), float(sy + oy)
