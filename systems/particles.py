"""Pooled particle system — dust, sparks, footsteps, signals."""

from __future__ import annotations

import math
import random

import pygame

MAX_PARTICLES = 180


def make_system(world_w: int = 3200, world_h: int = 2200, ambient: int = 55) -> dict:
    rng = random.Random(19)
    pool = []
    for _ in range(MAX_PARTICLES):
        pool.append(_dead())
    # Seed ambient dust as living
    living = 0
    for i in range(min(ambient, MAX_PARTICLES)):
        p = pool[i]
        p.update(
            {
                "alive": True,
                "kind": "dust",
                "x": rng.uniform(0, world_w),
                "y": rng.uniform(0, world_h),
                "vx": rng.uniform(8, 35),
                "vy": rng.uniform(-4, 6),
                "life": 9999.0,
                "max_life": 9999.0,
                "size": rng.randint(1, 3),
                "alpha": rng.randint(50, 130),
                "color": (255, 190, 130),
                "gravity": 0.0,
            }
        )
        living += 1
    return {"pool": pool, "world_w": world_w, "world_h": world_h, "rng": rng}


def _dead() -> dict:
    return {
        "alive": False,
        "kind": "dust",
        "x": 0.0,
        "y": 0.0,
        "vx": 0.0,
        "vy": 0.0,
        "life": 0.0,
        "max_life": 1.0,
        "size": 1,
        "alpha": 0,
        "color": (255, 200, 140),
        "gravity": 0.0,
    }


def _spawn(sys: dict, **kwargs) -> bool:
    for p in sys["pool"]:
        if not p["alive"]:
            p.update(_dead())
            p.update(kwargs)
            p["alive"] = True
            return True
    return False


def emit_footstep(sys: dict, x: float, y: float, running: bool = False) -> None:
    n = 3 if running else 2
    rng = sys["rng"]
    for _ in range(n):
        _spawn(
            sys,
            kind="sand",
            x=x + rng.uniform(-6, 6),
            y=y + rng.uniform(-2, 4),
            vx=rng.uniform(-20, 20),
            vy=rng.uniform(-30, -5),
            life=0.35,
            max_life=0.35,
            size=rng.randint(1, 3),
            alpha=160,
            color=(210, 140, 90),
            gravity=90,
        )


def emit_sparks(sys: dict, x: float, y: float) -> None:
    rng = sys["rng"]
    for _ in range(8):
        ang = rng.uniform(0, math.tau)
        spd = rng.uniform(40, 120)
        _spawn(
            sys,
            kind="spark",
            x=x,
            y=y,
            vx=math.cos(ang) * spd,
            vy=math.sin(ang) * spd - 40,
            life=rng.uniform(0.25, 0.55),
            max_life=0.55,
            size=2,
            alpha=255,
            color=(255, 220, 120),
            gravity=180,
        )


def emit_pickup(sys: dict, x: float, y: float) -> None:
    rng = sys["rng"]
    for _ in range(10):
        ang = rng.uniform(0, math.tau)
        _spawn(
            sys,
            kind="pickup",
            x=x,
            y=y,
            vx=math.cos(ang) * rng.uniform(20, 70),
            vy=math.sin(ang) * rng.uniform(20, 70) - 30,
            life=0.5,
            max_life=0.5,
            size=3,
            alpha=220,
            color=(140, 230, 180),
            gravity=40,
        )


def emit_signal(sys: dict, x: float, y: float) -> None:
    _spawn(
        sys,
        kind="signal",
        x=x,
        y=y,
        vx=0,
        vy=0,
        life=0.8,
        max_life=0.8,
        size=8,
        alpha=180,
        color=(90, 220, 160),
        gravity=0,
    )


def update(sys: dict, dt: float, wind=None) -> None:
    ww, wh = sys["world_w"], sys["world_h"]
    wx = wy = 0.0
    if wind is not None:
        wx = wind["dir_x"] * wind["strength"] * 25.0
        wy = wind["dir_y"] * wind["strength"] * 12.0

    for p in sys["pool"]:
        if not p["alive"]:
            continue
        if p["kind"] == "dust" and p["life"] > 100:
            # Ambient looping dust
            p["x"] += (p["vx"] + wx) * dt
            p["y"] += (p["vy"] + wy * 0.5) * dt
            if p["x"] > ww:
                p["x"] = 0
            if p["x"] < 0:
                p["x"] = ww
            if p["y"] > wh:
                p["y"] = 0
            if p["y"] < 0:
                p["y"] = wh
            continue

        p["life"] -= dt
        if p["life"] <= 0:
            p["alive"] = False
            continue
        p["vy"] += p["gravity"] * dt
        p["x"] += (p["vx"] + wx * 0.3) * dt
        p["y"] += (p["vy"] + wy * 0.2) * dt
        if p["kind"] == "signal":
            p["size"] = int(8 + (1 - p["life"] / p["max_life"]) * 28)


def draw(surface, sys: dict, cam: dict) -> None:
    layer = pygame.Surface((cam["view_w"], cam["view_h"]), pygame.SRCALPHA)
    for p in sys["pool"]:
        if not p["alive"]:
            continue
        sx = int(p["x"] - cam["x"])
        sy = int(p["y"] - cam["y"])
        if sx < -20 or sy < -20 or sx > cam["view_w"] + 20 or sy > cam["view_h"] + 20:
            continue
        if p["kind"] == "dust" and p["life"] > 100:
            alpha = p["alpha"]
        else:
            alpha = int(p["alpha"] * max(0.0, p["life"] / max(0.01, p["max_life"])))
        col = (*p["color"], max(0, min(255, alpha)))
        if p["kind"] == "signal":
            pygame.draw.circle(layer, col, (sx, sy), max(2, p["size"]), 1)
        else:
            pygame.draw.circle(layer, col, (sx, sy), max(1, p["size"]))
    surface.blit(layer, (0, 0))


# Back-compat aliases used by older main wiring
def make_dust(count=55, world_w=3200, world_h=2200, seed=19):
    return make_system(world_w, world_h, ambient=count)


def update_dust(particles, dt, world_w, world_h, wind=None):
    # Old API passed a list; new API uses system dict
    if isinstance(particles, dict) and "pool" in particles:
        update(particles, dt, wind=wind)
    else:
        # legacy list — no-op safe
        pass


def draw_dust(surface, particles, cam):
    if isinstance(particles, dict) and "pool" in particles:
        draw(surface, particles, cam)
