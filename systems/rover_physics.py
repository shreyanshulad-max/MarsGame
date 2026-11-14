"""Velocity-based top-down rover physics for Challenge 3 driving."""

from __future__ import annotations

import math

# Tunable handling — Grades 5–8 accessible arcade model (not a harsh sim)
CONFIG = {
    "max_forward": 210.0,
    "max_reverse": 95.0,
    "accel": 165.0,
    "brake": 290.0,
    "coast_friction": 75.0,
    "steer_rate": 128.0,       # deg/s at reference speed
    "steer_min_factor": 0.42,   # still turnable when nearly stopped
    "steer_speed_ref": 160.0,
    "high_speed_steer_scale": 0.72,
    "lateral_grip": 9.5,       # 1/s damping of sideways slip
    "max_angular": 155.0,      # deg/s
    "collision_bounce": 0.22,
    "collision_slide": 0.55,
    "hit_slow_time": 0.4,
    "assisted_steer_blend": 0.18,  # mild auto-correct toward destination when assisted
    "handbrake_grip": 0.35,
    "handbrake_steer_boost": 1.25,
}


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def wrap_heading(deg: float) -> float:
    return deg % 360.0


def init_motion(ch3: dict) -> None:
    """Ensure physics fields exist on challenge state."""
    ch3.setdefault("speed", 0.0)           # forward velocity (px/s)
    ch3.setdefault("lateral", 0.0)         # lateral slip (px/s)
    ch3.setdefault("angular_vel", 0.0)     # deg/s
    ch3.setdefault("heading", 0.0)
    ch3.setdefault("chassis_bob", 0.0)
    ch3.setdefault("impact_shake", 0.0)
    ch3.setdefault("assisted_steer", True)
    ch3.setdefault("handbrake", False)


def step(
    ch3: dict,
    dt: float,
    throttle: float,
    steer: float,
    handbrake: bool,
    terrain: dict,
    world_w: float,
    world_h: float,
    obstacles: list,
    target: tuple[float, float] | None = None,
) -> dict:
    """
    Advance rover physics by dt seconds.
    terrain: dict from rover_terrain.sample()
    obstacles: list of pygame.Rect (solid)
    Returns event flags: {hit, moved}.
    """
    init_motion(ch3)
    cfg = CONFIG
    if ch3.get("rescued"):
        ch3["speed"] = 0.0
        ch3["lateral"] = 0.0
        ch3["angular_vel"] = 0.0
        return {"hit": False, "moved": False}

    if ch3.get("hit_timer", 0) > 0:
        ch3["hit_timer"] -= dt
    if ch3.get("hit_message_timer", 0) > 0:
        ch3["hit_message_timer"] -= dt
    if ch3.get("impact_shake", 0) > 0:
        ch3["impact_shake"] = max(0.0, ch3["impact_shake"] - dt * 3.0)

    grip = float(terrain.get("grip", 1.0))
    resist = float(terrain.get("resistance", 1.0))
    accel_mul = float(terrain.get("accel", 1.0))
    route_trac = float(ch3.get("traction_mod", 1.0))
    if ch3.get("hit_timer", 0) > 0:
        grip *= 0.45
        accel_mul *= 0.5
    if not ch3.get("repair_ok"):
        grip *= 0.6
        accel_mul *= 0.55

    grip *= route_trac
    accel_mul *= route_trac

    # Throttle / brake / reverse
    speed = float(ch3["speed"])
    if throttle > 0:
        speed += cfg["accel"] * accel_mul * throttle * dt
    elif throttle < 0:
        if speed > 5.0:
            speed -= cfg["brake"] * abs(throttle) * dt
        else:
            speed -= cfg["accel"] * 0.55 * accel_mul * abs(throttle) * dt
    else:
        # Coast
        if speed > 0:
            speed = max(0.0, speed - cfg["coast_friction"] * resist * dt)
        elif speed < 0:
            speed = min(0.0, speed + cfg["coast_friction"] * resist * dt)

    if handbrake:
        speed *= max(0.0, 1.0 - (1.2 * dt))
        grip *= cfg["handbrake_grip"]

    max_fwd = cfg["max_forward"] * grip
    max_rev = -cfg["max_reverse"] * grip
    speed = clamp(speed, max_rev, max_fwd)
    ch3["speed"] = speed

    # Steering — speed-dependent, capped angular velocity
    spd_abs = abs(speed)
    if spd_abs < 6.0 and abs(steer) > 0.1 and throttle == 0 and not handbrake:
        # Creep-turn: allow slow pivot when nearly stopped with steer held
        speed_factor = cfg["steer_min_factor"] * 0.5
    else:
        speed_factor = clamp(spd_abs / cfg["steer_speed_ref"], cfg["steer_min_factor"], 1.0)
        if spd_abs > cfg["steer_speed_ref"]:
            speed_factor *= cfg["high_speed_steer_scale"]

    steer_input = steer
    if handbrake:
        steer_input *= cfg["handbrake_steer_boost"]

    # Mild assisted steering toward target (accessibility)
    if ch3.get("assisted_steer") and target and spd_abs > 20 and abs(steer) < 0.2:
        desired = math.degrees(math.atan2(target[1] - ch3["rover_y"], target[0] - ch3["rover_x"]))
        err = (desired - ch3["heading"] + 180) % 360 - 180
        steer_input += clamp(err / 45.0, -1.0, 1.0) * cfg["assisted_steer_blend"]

    ang = steer_input * cfg["steer_rate"] * speed_factor * grip * dt
    # Rocky instability
    ang += float(terrain.get("steer_noise", 0.0)) * dt
    ang = clamp(ang, -cfg["max_angular"] * dt, cfg["max_angular"] * dt)
    ch3["heading"] = wrap_heading(ch3["heading"] + ang)
    ch3["angular_vel"] = ang / max(dt, 1e-6)

    # Lateral slip from yaw, then damp
    rad = math.radians(ch3["heading"])
    # Convert heading change into a bit of lateral
    ch3["lateral"] += -math.sin(math.radians(ang)) * spd_abs * 0.15
    lat_damp = cfg["lateral_grip"] * grip
    ch3["lateral"] *= max(0.0, 1.0 - lat_damp * dt)
    ch3["lateral"] = clamp(ch3["lateral"], -80.0, 80.0)

    # World velocity
    fwd_x = math.cos(rad) * speed
    fwd_y = math.sin(rad) * speed
    lat_x = -math.sin(rad) * ch3["lateral"]
    lat_y = math.cos(rad) * ch3["lateral"]
    vx = (fwd_x + lat_x) * (1.0 / max(0.35, resist))
    vy = (fwd_y + lat_y) * (1.0 / max(0.35, resist))

    old_x, old_y = float(ch3["rover_x"]), float(ch3["rover_y"])
    new_x = clamp(old_x + vx * dt, 50.0, world_w - 50.0)
    new_y = clamp(old_y + vy * dt, 50.0, world_h - 50.0)

    hit = False
    # Axis-separated collision resolution (slide along obstacles)
    half_w, half_h = 36, 22
    test_x = _rect(new_x, old_y, half_w, half_h)
    if _blocked(test_x, obstacles):
        new_x = old_x
        # deflect lateral
        ch3["speed"] *= (1.0 - cfg["collision_bounce"])
        ch3["lateral"] *= -cfg["collision_slide"]
        hit = True
    test_y = _rect(new_x, new_y, half_w, half_h)
    if _blocked(test_y, obstacles):
        new_y = old_y
        ch3["speed"] *= (1.0 - cfg["collision_bounce"])
        ch3["lateral"] *= -cfg["collision_slide"]
        hit = True
    # Corner catch
    if _blocked(_rect(new_x, new_y, half_w, half_h), obstacles):
        new_x, new_y = old_x, old_y
        ch3["speed"] *= -cfg["collision_bounce"]
        hit = True

    if hit:
        ch3["hit_timer"] = cfg["hit_slow_time"]
        ch3["hit_message_timer"] = 0.75
        ch3["impact_shake"] = 1.0

    moved = abs(new_x - old_x) + abs(new_y - old_y)
    ch3["rover_x"] = new_x
    ch3["rover_y"] = new_y
    ch3["wheel_spin"] = float(ch3.get("wheel_spin", 0.0)) + moved * 0.14
    # Chassis bob from rocky terrain / motion
    bob_src = float(terrain.get("vibration", 0.0)) * (0.4 + spd_abs / 200.0)
    ch3["chassis_bob"] = math.sin(ch3["wheel_spin"] * 0.35) * bob_src * 3.0

    return {"hit": hit, "moved": moved > 0.05, "moved_px": moved}


def _rect(x, y, hw, hh):
    import pygame
    return pygame.Rect(int(x - hw), int(y - hh), int(hw * 2), int(hh * 2))


def _blocked(rect, obstacles) -> bool:
    for ob in obstacles:
        if rect.colliderect(ob):
            return True
    return False
