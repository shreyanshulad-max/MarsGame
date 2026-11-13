"""Astronaut — velocity physics, terrain response, procedural animation."""

from __future__ import annotations

import math

import pygame

from . import collision

# Tunable movement constants
ACCEL = 980.0
FRICTION = 1400.0
MAX_WALK = 170.0
MAX_RUN = 275.0
ASTRO_RADIUS = 13
WIND_MAX_INFLUENCE = 22.0  # px/s^2 cap already in wind module


def make_astronaut(spawn) -> dict:
    return {
        "x": float(spawn[0]),
        "y": float(spawn[1]),
        "vx": 0.0,
        "vy": 0.0,
        "facing_x": 0.0,
        "facing_y": 1.0,
        "facing": "down",
        "moving": False,
        "running": False,
        "anim_t": 0.0,
        "anim_state": "idle",
        "status": "NOMINAL",
        "hold_e": 0.0,
        "step_timer": 0.0,
        "bump_flash": 0.0,
        "interact_timer": 0.0,
    }


def _facing_name(fx: float, fy: float) -> str:
    if abs(fx) > abs(fy) * 1.1:
        return "left" if fx < 0 else "right"
    if abs(fy) > abs(fx) * 1.1:
        return "up" if fy < 0 else "down"
    # diagonals map to dominant axis for 4-dir art
    if abs(fx) >= abs(fy):
        return "left" if fx < 0 else "right"
    return "up" if fy < 0 else "down"


def set_anim(astro: dict, state: str, duration: float = 0.35) -> None:
    if state in ("inspect", "interact", "repair", "collect", "scan"):
        astro["anim_state"] = state
        astro["interact_timer"] = duration


def move_astronaut(
    astro: dict,
    keys,
    colliders,
    dt: float,
    world_w: int,
    world_h: int,
    terrain_props: dict | None = None,
    wind_accel: tuple[float, float] = (0.0, 0.0),
    on_bump=None,
    on_step=None,
) -> None:
    """
    Velocity-based movement with accel/friction, terrain modifiers, wind nudge.
    Axis-separated collision with sliding. Prevents tunnelling via substeps.
    """
    if astro["bump_flash"] > 0:
        astro["bump_flash"] -= dt
    if astro["interact_timer"] > 0:
        astro["interact_timer"] -= dt
        if astro["interact_timer"] <= 0 and astro["anim_state"] not in ("idle", "walk", "run"):
            astro["anim_state"] = "idle"

    ix = iy = 0.0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        ix -= 1.0
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        ix += 1.0
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        iy -= 1.0
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        iy += 1.0

    running = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
    inputting = ix != 0.0 or iy != 0.0
    if inputting:
        length = math.hypot(ix, iy)
        ix /= length
        iy /= length
        astro["facing_x"] = ix
        astro["facing_y"] = iy
        astro["facing"] = _facing_name(ix, iy)

    speed_mul = 1.0
    fric_mul = 1.0
    if terrain_props:
        speed_mul = float(terrain_props.get("speed", 1.0))
        fric_mul = float(terrain_props.get("friction", 1.0))

    max_speed = (MAX_RUN if running and inputting else MAX_WALK) * speed_mul

    if inputting and astro["interact_timer"] <= 0:
        astro["vx"] += ix * ACCEL * dt
        astro["vy"] += iy * ACCEL * dt
    else:
        # Friction / deceleration when no input
        speed = math.hypot(astro["vx"], astro["vy"])
        if speed > 0.01:
            drop = FRICTION * fric_mul * dt
            new_speed = max(0.0, speed - drop)
            scale = new_speed / speed
            astro["vx"] *= scale
            astro["vy"] *= scale
        else:
            astro["vx"] = astro["vy"] = 0.0

    # Wind influence (already capped by caller)
    astro["vx"] += wind_accel[0] * dt
    astro["vy"] += wind_accel[1] * dt

    # Clamp to max speed
    speed = math.hypot(astro["vx"], astro["vy"])
    if speed > max_speed:
        scale = max_speed / speed
        astro["vx"] *= scale
        astro["vy"] *= scale
        speed = max_speed

    astro["moving"] = speed > 8.0
    astro["running"] = running and speed > MAX_WALK * 0.85 * speed_mul

    if astro["interact_timer"] > 0:
        pass  # keep special anim
    elif not astro["moving"]:
        astro["anim_state"] = "idle"
        astro["anim_t"] += dt * 2.2
    elif astro["running"]:
        astro["anim_state"] = "run"
        astro["anim_t"] += dt * 14.0
    else:
        astro["anim_state"] = "walk"
        astro["anim_t"] += dt * 9.0

    # Substep integration to reduce tunnelling when running
    steps = 2 if speed * dt > ASTRO_RADIUS * 0.6 else 1
    step_dt = dt / steps
    bumped = False
    for _ in range(steps):
        local = collision.nearby_colliders(astro["x"], astro["y"], colliders)
        # X
        new_x = astro["x"] + astro["vx"] * step_dt
        new_x = max(36.0, min(world_w - 36.0, new_x))
        test = collision.feet_rect(new_x, astro["y"], ASTRO_RADIUS)
        if collision.collides_any(test, local):
            astro["vx"] = 0.0
            bumped = True
        else:
            astro["x"] = new_x
        # Y
        new_y = astro["y"] + astro["vy"] * step_dt
        new_y = max(36.0, min(world_h - 36.0, new_y))
        test = collision.feet_rect(astro["x"], new_y, ASTRO_RADIUS)
        if collision.collides_any(test, local):
            astro["vy"] = 0.0
            bumped = True
        else:
            astro["y"] = new_y

    if bumped:
        astro["bump_flash"] = 0.15
        if on_bump:
            on_bump()

    # Footsteps
    if astro["moving"]:
        astro["step_timer"] -= dt
        interval = 0.22 if astro["running"] else 0.34
        if astro["step_timer"] <= 0:
            astro["step_timer"] = interval
            if on_step:
                on_step(astro["x"], astro["y"], astro["running"])


def draw_astronaut(surface, astro: dict, cam: dict, power_online: bool = False) -> None:
    sx = int(astro["x"] - cam["x"])
    sy = int(astro["y"] - cam["y"])
    if sx < -50 or sx > cam["view_w"] + 50 or sy < -70 or sy > cam["view_h"] + 50:
        return

    facing = astro.get("facing", "down")
    state = astro.get("anim_state", "idle")
    t = astro["anim_t"]

    if state == "idle":
        bob = int(math.sin(t) * 1.5)
        leg = 0
    elif state == "run":
        bob = int(math.sin(t) * 5)
        leg = int(math.sin(t) * 8)
    elif state in ("inspect", "interact", "repair", "collect", "scan"):
        bob = int(math.sin(t * 2) * 2)
        leg = 0
    else:
        bob = int(math.sin(t) * 3)
        leg = int(math.sin(t) * 5)

    # Ground shadow (elongated slightly with facing)
    sh_w = 34 if facing in ("left", "right") else 30
    pygame.draw.ellipse(surface, (65, 32, 22), (sx - sh_w // 2, sy + 2, sh_w, 12))

    suit = (236, 236, 242)
    accent = (210, 120, 60)
    pack = (165, 170, 180)
    boot = (195, 105, 50)
    visor = (18, 38, 88)
    if astro["bump_flash"] > 0:
        suit = (255, 200, 190)

    # Legs
    pygame.draw.rect(surface, suit, (sx - 11, sy - 20 + bob, 9, 20))
    pygame.draw.rect(surface, suit, (sx + 2, sy - 20 + bob, 9, 20))
    lx = -leg if facing == "left" else (leg if facing == "right" else 0)
    pygame.draw.rect(surface, boot, (sx - 12 + lx, sy - 2 + bob, 11, 7))
    pygame.draw.rect(surface, boot, (sx + 1 - lx, sy - 2 + bob, 11, 7))

    # Torso
    pygame.draw.rect(surface, suit, (sx - 13, sy - 42 + bob, 26, 26), border_radius=4)
    pygame.draw.rect(surface, accent, (sx - 13, sy - 30 + bob, 26, 5))
    if power_online:
        pygame.draw.circle(surface, (80, 220, 140), (sx + 8, sy - 36 + bob), 3)

    # Suit light / headlamp when facing
    if facing == "down":
        glow = pygame.Surface((40, 28), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 230, 180, 35), (0, 0, 40, 28))
        surface.blit(glow, (sx - 20, sy - 10 + bob))

    # Backpack + arms by facing
    if facing == "left":
        pygame.draw.rect(surface, pack, (sx + 8, sy - 40 + bob, 11, 20), border_radius=2)
        arm_ext = 4 if state in ("interact", "repair", "collect") else 0
        pygame.draw.rect(surface, suit, (sx - 19 - arm_ext, sy - 38 + bob, 7 + arm_ext, 16))
        pygame.draw.rect(surface, suit, (sx + 9, sy - 36 + bob, 7, 14))
    elif facing == "right":
        pygame.draw.rect(surface, pack, (sx - 18, sy - 40 + bob, 11, 20), border_radius=2)
        arm_ext = 4 if state in ("interact", "repair", "collect") else 0
        pygame.draw.rect(surface, suit, (sx + 12, sy - 38 + bob, 7 + arm_ext, 16))
        pygame.draw.rect(surface, suit, (sx - 16, sy - 36 + bob, 7, 14))
    else:
        pygame.draw.rect(surface, pack, (sx - 8, sy - 40 + bob, 16, 12), border_radius=2)
        pygame.draw.rect(surface, suit, (sx - 18, sy - 38 + bob, 7, 15))
        pygame.draw.rect(surface, suit, (sx + 11, sy - 38 + bob, 7, 15))
        if state in ("interact", "repair", "collect", "scan"):
            pygame.draw.rect(surface, suit, (sx - 4, sy - 48 + bob, 8, 10))

    # Helmet
    pygame.draw.circle(surface, (248, 248, 252), (sx, sy - 52 + bob), 13)
    pygame.draw.circle(surface, (200, 205, 215), (sx, sy - 52 + bob), 13, 1)
    if facing == "left":
        pygame.draw.ellipse(surface, visor, (sx - 12, sy - 58 + bob, 12, 11))
    elif facing == "right":
        pygame.draw.ellipse(surface, visor, (sx, sy - 58 + bob, 12, 11))
    elif facing == "up":
        pygame.draw.ellipse(surface, (200, 205, 215), (sx - 6, sy - 58 + bob, 12, 8))
    else:
        pygame.draw.ellipse(surface, visor, (sx - 7, sy - 58 + bob, 14, 11))
        # Visor highlight
        pygame.draw.line(surface, (120, 180, 255), (sx - 4, sy - 56 + bob), (sx + 2, sy - 52 + bob), 1)
