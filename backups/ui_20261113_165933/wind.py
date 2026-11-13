"""Environmental wind — gusts affect dust and gently nudge exposed movement."""

from __future__ import annotations

import math
import random


def make_wind(seed: int = 7) -> dict:
    rng = random.Random(seed)
    angle = rng.uniform(0, math.tau)
    return {
        "angle": angle,
        "base": 0.35,
        "strength": 0.35,
        "gust": 0.0,
        "gust_timer": rng.uniform(4.0, 9.0),
        "dir_x": math.cos(angle),
        "dir_y": math.sin(angle) * 0.45,
        "t": 0.0,
    }


def update_wind(wind: dict, dt: float) -> None:
    wind["t"] += dt
    # Slow direction drift
    wind["angle"] += math.sin(wind["t"] * 0.07) * 0.15 * dt
    wind["dir_x"] = math.cos(wind["angle"])
    wind["dir_y"] = math.sin(wind["angle"]) * 0.4

    wind["gust_timer"] -= dt
    if wind["gust_timer"] <= 0:
        wind["gust"] = random.uniform(0.4, 1.0)
        wind["gust_timer"] = random.uniform(5.0, 12.0)
    else:
        wind["gust"] = max(0.0, wind["gust"] - dt * 0.35)

    wind["strength"] = wind["base"] + wind["gust"] * 0.55


def wind_force(wind: dict, exposed: bool = True) -> tuple[float, float]:
    """World-space acceleration nudge. Cap so player stays in control."""
    if not exposed:
        return 0.0, 0.0
    mag = 28.0 * wind["strength"]  # gentle
    return wind["dir_x"] * mag, wind["dir_y"] * mag
