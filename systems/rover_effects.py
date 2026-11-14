"""Dust particles and tyre tracks for the Challenge 3 rover."""

from __future__ import annotations

import math
import random

from systems import runtime_paths as rpaths

ROOT = rpaths.resource_root()

MAX_DUST = 90
MAX_TRACKS = 120
MAX_DEBRIS = 40


def make_effects() -> dict:
    return {
        "dust": [],
        "tracks": [],
        "debris": [],
        "storm_particles": [],
    }


def ensure(ch3: dict) -> dict:
    fx = ch3.get("effects")
    if not isinstance(fx, dict):
        fx = make_effects()
        ch3["effects"] = fx
    fx.setdefault("dust", [])
    fx.setdefault("tracks", [])
    fx.setdefault("debris", [])
    fx.setdefault("storm_particles", [])
    return fx


def wheel_world_positions(x: float, y: float, heading: float) -> list[tuple[float, float]]:
    rad = math.radians(heading)
    c, s = math.cos(rad), math.sin(rad)
    offsets = ((-28, 18), (0, 18), (28, 18), (-28, -18), (0, -18), (28, -18))
    out = []
    for ox, oy in offsets:
        out.append((x + ox * c - oy * s, y + ox * s + oy * c))
    return out


def emit_motion(ch3: dict, terrain: dict, moved_px: float, storm: float, dt: float) -> None:
    fx = ensure(ch3)
    spd = abs(float(ch3.get("speed", 0.0)))
    if moved_px < 0.4 or spd < 12:
        return
    dust_rate = float(terrain.get("dust", 0.2))
    track_rate = float(terrain.get("tracks", 0.2))
    rng = random
    wheels = wheel_world_positions(ch3["rover_x"], ch3["rover_y"], ch3["heading"])

    # Tracks on sand / soft surfaces
    if track_rate > 0.2 and spd > 25 and rng.random() < min(1.0, track_rate * 0.55):
        for wx, wy in (wheels[0], wheels[2], wheels[3], wheels[5]):
            fx["tracks"].append(
                {
                    "x": wx,
                    "y": wy,
                    "h": ch3["heading"],
                    "life": 3.2,
                    "max": 3.2,
                    "w": 5,
                }
            )
        if len(fx["tracks"]) > MAX_TRACKS:
            fx["tracks"] = fx["tracks"][-MAX_TRACKS:]

    # Wheel dust
    if dust_rate > 0.1 and rng.random() < min(0.9, dust_rate * 0.4 + spd / 600.0):
        for wx, wy in wheels[::2]:
            wind = 40 + storm * 90
            fx["dust"].append(
                {
                    "x": wx + rng.uniform(-4, 4),
                    "y": wy + rng.uniform(-4, 4),
                    "vx": rng.uniform(-20, 20) + wind * 0.15,
                    "vy": rng.uniform(-30, -5),
                    "life": rng.uniform(0.35, 0.9),
                    "max": 0.9,
                    "size": rng.randint(2, 5) + int(dust_rate * 2),
                    "alpha": rng.randint(90, 180),
                }
            )
        if len(fx["dust"]) > MAX_DUST:
            fx["dust"] = fx["dust"][-MAX_DUST:]

    # Rocky debris flecks
    if terrain.get("id") == "rocky" and rng.random() < 0.12:
        wx, wy = wheels[rng.randint(0, 5)]
        fx["debris"].append(
            {
                "x": wx,
                "y": wy,
                "vx": rng.uniform(-40, 40),
                "vy": rng.uniform(-50, -10),
                "life": 0.4,
                "size": rng.randint(1, 3),
            }
        )
        if len(fx["debris"]) > MAX_DEBRIS:
            fx["debris"] = fx["debris"][-MAX_DEBRIS:]


def emit_impact(ch3: dict) -> None:
    fx = ensure(ch3)
    rng = random
    for _ in range(8):
        fx["dust"].append(
            {
                "x": ch3["rover_x"] + rng.uniform(-20, 20),
                "y": ch3["rover_y"] + rng.uniform(-12, 12),
                "vx": rng.uniform(-60, 60),
                "vy": rng.uniform(-40, 40),
                "life": 0.5,
                "max": 0.5,
                "size": rng.randint(3, 6),
                "alpha": 200,
            }
        )


def ensure_storm_field(ch3: dict, count: int = 55) -> None:
    fx = ensure(ch3)
    if fx["storm_particles"]:
        return
    rng = random.Random(3)
    for _ in range(count):
        fx["storm_particles"].append(
            {
                "x": rng.uniform(0, 1280),
                "y": rng.uniform(0, 720),
                "speed": rng.uniform(1.2, 3.5),
                "size": rng.randint(1, 4),
                "alpha": rng.randint(50, 140),
            }
        )


def update(ch3: dict, dt: float, storm: float) -> None:
    fx = ensure(ch3)
    wind = 30 + storm * 140
    gust = 1.0 + (0.35 if storm > 0.6 and int(ch3.get("time_left", 0) * 4) % 7 == 0 else 0.0)

    alive = []
    for p in fx["dust"]:
        p["life"] -= dt
        if p["life"] <= 0:
            continue
        p["x"] += (p["vx"] + wind * 0.25 * gust) * dt
        p["y"] += p["vy"] * dt
        p["vy"] += 40 * dt
        alive.append(p)
    fx["dust"] = alive

    tracks = []
    for t in fx["tracks"]:
        t["life"] -= dt
        if t["life"] > 0:
            tracks.append(t)
    fx["tracks"] = tracks

    debris = []
    for d in fx["debris"]:
        d["life"] -= dt
        if d["life"] <= 0:
            continue
        d["x"] += d["vx"] * dt
        d["y"] += d["vy"] * dt
        debris.append(d)
    fx["debris"] = debris

    ensure_storm_field(ch3)
    for p in fx["storm_particles"]:
        p["x"] += p["speed"] * (1.0 + storm * 2.8) * gust
        p["y"] += math.sin(p["x"] * 0.02) * 0.5
        if p["x"] > 1285:
            p["x"] = -5
            p["y"] = random.uniform(0, 720)


def draw_world(surface, ch3: dict, camera: tuple[float, float]) -> None:
    """Draw tracks/dust/debris in world space via camera offset."""
    import pygame

    fx = ensure(ch3)
    cam_x, cam_y = camera
    for t in fx["tracks"]:
        a = max(0, min(180, int(160 * (t["life"] / t["max"]))))
        sx, sy = int(t["x"] - cam_x), int(t["y"] - cam_y)
        if -20 <= sx <= 1300 and -20 <= sy <= 740:
            pygame.draw.circle(surface, (95, 48, 30, a) if False else (100, 50, 32), (sx, sy), t.get("w", 4))

    for p in fx["dust"]:
        sx, sy = int(p["x"] - cam_x), int(p["y"] - cam_y)
        if -10 <= sx <= 1290 and -10 <= sy <= 730:
            alpha = max(0, min(220, int(p["alpha"] * (p["life"] / max(0.01, p["max"])))))
            # Soft circles via small solid dots (fast)
            pygame.draw.circle(surface, (220, 170, 120), (sx, sy), p["size"])

    for d in fx["debris"]:
        sx, sy = int(d["x"] - cam_x), int(d["y"] - cam_y)
        if 0 <= sx <= 1280 and 0 <= sy <= 720:
            pygame.draw.circle(surface, (90, 70, 55), (sx, sy), d["size"])


def draw_storm_screen(surface, ch3: dict, storm: float) -> None:
    """Screen-space storm overlay particles + tint (HUD stays readable)."""
    import pygame

    fx = ensure(ch3)
    ensure_storm_field(ch3)
    dust = pygame.Surface((1280, 720), pygame.SRCALPHA)
    for p in fx["storm_particles"]:
        alpha = min(210, int(p["alpha"] * (0.35 + storm * 0.9)))
        pygame.draw.circle(
            dust,
            (255, 190, 130, alpha),
            (int(p["x"]), int(p["y"])),
            p["size"] + int(storm * 2),
        )
    surface.blit(dust, (0, 0))
    overlay = pygame.Surface((1280, 720), pygame.SRCALPHA)
    # Cap haze so nearby obstacles remain visible
    overlay.fill((175, 95, 45, int(20 + storm * 85)))
    surface.blit(overlay, (0, 0))
