"""Minimal exploration HUD — world stays the visual focus."""

from __future__ import annotations

import math

import pygame

from systems import challenge_ui as ui
from systems import inventory as inv_sys
from systems import minimap


def _status_ok(value: str) -> bool:
    return value in ("ONLINE", "SAFE", "RESCUED", "NOMINAL")


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
    status_detail=None,
):
    """
    Layout:
      Top-left  — one objective card
      Top-right — compact status chips (+ optional detail popover)
      Bottom-right — compact minimap
      Center-bottom — interaction prompt only when near target
    """
    # ---- Top-left: objective only ----
    title = ""
    task = ""
    if guide_obj:
        title = guide_obj.get("title") or "Objective"
        task = guide_obj.get("task") or ""
    else:
        # Fallback: truncate legacy objective string
        title = (objective or "Explore")[:48]
        task = ""
        if inventory is not None and mission_hint:
            missing = inv_sys.missing_for_mission(inventory, mission_hint)
            if missing:
                task = "Missing: " + ", ".join(n for n, _ in missing[:2])

    obj_w = 380
    obj_h = 56 if not task else 72
    ui.soft_panel(surface, pygame.Rect(ui.MARGIN, ui.MARGIN, obj_w, obj_h), 200)
    ui.label(surface, fonts, ui.truncate(title, 36), (ui.MARGIN + 14, ui.MARGIN + 10), ui.C_TEXT, "body")
    if task:
        ui.label(surface, fonts, ui.truncate(task, 44), (ui.MARGIN + 14, ui.MARGIN + 36), ui.C_MUTED, "small")

    # ---- Top-right: compact status chips ----
    chip_x = surface.get_width() - 168 - 16
    # Leave room above minimap — chips sit left of minimap column
    chip_x = surface.get_width() - 360
    statuses = [
        ("COMM", communication_status),
        ("PWR", power_status),
        ("RVR", rover_status),
    ]
    for i, (lab, val) in enumerate(statuses):
        ok = _status_ok(val)
        short = val[:8]
        ui.status_chip(surface, fonts, f"{lab} {short}", (chip_x, ui.MARGIN + i * 30), ok, width=150)

    # Optional detail when requested (click handled elsewhere via status_detail flag)
    if status_detail:
        detail = pygame.Rect(chip_x - 200, ui.MARGIN, 190, 110)
        ui.soft_panel(surface, detail, 220)
        ui.label(surface, fonts, "SYSTEMS", (detail.x + 12, detail.y + 8), ui.C_MUTED, "small")
        rows = [
            ("Comm", communication_status),
            ("Power", power_status),
            ("Food", food_status),
            ("Rover", rover_status),
        ]
        for i, (lab, val) in enumerate(rows):
            col = ui.C_GREEN if _status_ok(val) else ui.C_AMBER
            ui.label(surface, fonts, f"{lab}: {val}", (detail.x + 12, detail.y + 28 + i * 18), col, "small")

    # ---- Interaction prompt (contextual only) ----
    if prompt:
        pulse = 0.92 + 0.08 * abs(math.sin(pygame.time.get_ticks() * 0.004))
        bw, bh = 480, 40
        bx = surface.get_width() // 2 - bw // 2
        by = surface.get_height() - 78
        s = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(s, (*ui.C_BG, int(210 * pulse)), (0, 0, bw, bh), border_radius=8)
        pygame.draw.rect(s, (*ui.C_SIGNAL, 180), (0, 0, bw, bh), 1, border_radius=8)
        surface.blit(s, (bx, by))
        label = fonts["small"].render(prompt[:56], True, ui.C_TEXT)
        surface.blit(label, label.get_rect(center=(surface.get_width() // 2, by + bh // 2)))

    # Quiet control strip (secondary — no panel)
    hint = fonts["small"].render(
        "WASD  E  Tab  I  C  M  G  J  Esc",
        True,
        ui.C_MUTED,
    )
    surface.blit(hint, (ui.MARGIN, surface.get_height() - 22))

    # ---- Minimap (compact, bottom-right) ----
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
        ui.dim_backdrop(surface, 150)
        box = pygame.Rect(440, 250, 400, 200)
        ui.panel(surface, box, accent=ui.C_MARS)
        ui.centered(surface, fonts, "PAUSED", (box.centerx, 300), ui.C_TEXT, "title")
        ui.centered(surface, fonts, "Esc — Resume", (box.centerx, 350), ui.C_MUTED, "body")
        ui.centered(surface, fonts, "Q — Quit", (box.centerx, 390), ui.C_AMBER, "body")
