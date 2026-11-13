"""Exploration HUD (screen-fixed)."""

from __future__ import annotations

import math

import pygame

from . import inventory as inv_sys
from . import minimap


HUD_BG = (20, 12, 10)
HUD_TEXT = (255, 230, 200)
HUD_WARN = (255, 180, 80)
HUD_ALERT = (255, 90, 70)
HUD_OK = (120, 220, 140)


def draw_explore_hud(
    surface,
    fonts,
    astro,
    colony,
    cam,
    communication_status,
    power_status,
    food_status,
    rover_status,
    score,
    zone_name,
    objective,
    collect_count,
    prompt="",
    paused=False,
    discovery=None,
    inventory=None,
    mission_hint=None,
    guide_obj=None,
):
    # Left status card
    panel = pygame.Surface((460, 200), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*HUD_BG, 185), (0, 0, 460, 200), border_radius=10)
    pygame.draw.rect(panel, (255, 180, 100, 140), (0, 0, 460, 200), 2, border_radius=10)
    surface.blit(panel, (16, 16))

    surface.blit(fonts["title"].render("MARS MISSION", True, HUD_TEXT), (32, 24))
    surface.blit(fonts["small"].render(f"ZONE: {zone_name}", True, HUD_WARN), (32, 56))

    def row(label, value, y):
        color = HUD_OK if value in ("ONLINE", "SAFE", "RESCUED", "NOMINAL") else HUD_WARN
        if value in ("OFFLINE", "AT RISK", "MISSING"):
            color = HUD_ALERT
        surface.blit(fonts["small"].render(f"{label}: {value}", True, color), (32, y))

    row("COMM", communication_status, 82)
    row("POWER", power_status, 104)
    row("FOOD", food_status, 126)
    row("ROVER", rover_status, 148)
    surface.blit(
        fonts["small"].render(
            f"ASTRONAUT: {astro.get('status', 'NOMINAL')}   SCORE: {score}   SUPPLIES: {collect_count}",
            True,
            HUD_TEXT,
        ),
        (32, 172),
    )

    # Objective strip
    obj = pygame.Surface((620, 56), pygame.SRCALPHA)
    pygame.draw.rect(obj, (*HUD_BG, 180), (0, 0, 620, 56), border_radius=8)
    pygame.draw.rect(obj, (90, 200, 220, 140), (0, 0, 620, 56), 2, border_radius=8)
    surface.blit(obj, (16, 228))
    surface.blit(fonts["small"].render(f"OBJECTIVE: {objective}", True, HUD_TEXT), (28, 236))
    if inventory is not None and mission_hint:
        missing = inv_sys.missing_for_mission(inventory, mission_hint)
        if missing:
            tip = "Missing: " + ", ".join(f"{n} (~{loc})" for n, loc in missing[:2])
            surface.blit(fonts["small"].render(tip[:70], True, HUD_ALERT), (28, 258))
        else:
            surface.blit(fonts["small"].render("Required supplies ready for station work.", True, HUD_OK), (28, 258))

    hint = fonts["small"].render(
        "WASD | E interact | Tab scan | I inv | C campaign | M map | G guide | J journal | Esc",
        True,
        HUD_TEXT,
    )
    surface.blit(hint, (16, surface.get_height() - 28))

    if prompt:
        pulse = 0.85 + 0.15 * abs(math.sin(pygame.time.get_ticks() * 0.006))
        banner = pygame.Surface((620, 52), pygame.SRCALPHA)
        pygame.draw.rect(banner, (*HUD_BG, int(220 * pulse)), (0, 0, 620, 52), border_radius=12)
        pygame.draw.rect(banner, (80, 220, 180, 220), (0, 0, 620, 52), 2, border_radius=12)
        surface.blit(banner, (surface.get_width() // 2 - 310, surface.get_height() - 90))
        label = fonts["body"].render(prompt, True, HUD_OK)
        surface.blit(label, label.get_rect(center=(surface.get_width() // 2, surface.get_height() - 64)))

    minimap.draw_minimap(
        surface,
        fonts,
        astro,
        colony,
        cam,
        colony["world_w"],
        colony["world_h"],
        discovery=discovery,
        objective=objective,
        guide_obj=guide_obj,
    )

    if paused:
        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surface.blit(dim, (0, 0))
        box = pygame.Rect(440, 240, 400, 220)
        pygame.draw.rect(surface, (28, 16, 12), box, border_radius=14)
        pygame.draw.rect(surface, (255, 170, 90), box, 3, border_radius=14)
        surface.blit(fonts["title"].render("PAUSED", True, HUD_TEXT), (box.centerx - 60, 270))
        surface.blit(fonts["body"].render("Esc — Resume", True, HUD_WARN), (box.centerx - 80, 330))
        surface.blit(fonts["body"].render("Q — Quit to desktop", True, HUD_ALERT), (box.centerx - 100, 375))
