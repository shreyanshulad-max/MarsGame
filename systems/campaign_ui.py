"""Campaign dashboard, mission report, and final report panels."""

from __future__ import annotations

import pygame

from systems import campaign as camp
from systems import challenge_ui as ui
from systems import materials as mats


def draw_dashboard(surface, fonts, mouse_pos, campaign: dict, inventory: dict) -> dict:
    ui.dim_backdrop(surface, 160)
    box = pygame.Rect(100, 48, 1080, 624)
    ui.panel(surface, box)
    y = ui.header(
        surface, fonts, box,
        "CAMPAIGN",
        f"Stage {campaign.get('current_campaign_stage')}   ·   Seed {campaign.get('campaign_seed')}",
    )

    # Single stats row under header divider
    ui.label(
        surface, fonts,
        f"Mission Score  {campaign['mission_score']}      Research Points  {campaign['research_points']} RP      Tier  {campaign.get('research_tier', 1)}",
        (140, y + 4),
        ui.C_SIGNAL,
        "small",
    )

    y = y + 36
    for mid in camp.MISSION_ORDER:
        meta = camp.MISSION_META[mid]
        st = camp.mission_status(campaign, mid)
        color = {
            camp.STATUS_COMPLETED: ui.C_GREEN,
            camp.STATUS_AVAILABLE: ui.C_MARS,
            camp.STATUS_IN_PROGRESS: ui.C_SIGNAL,
            camp.STATUS_LOCKED: ui.C_MUTED,
        }.get(st, ui.C_MUTED)
        row = pygame.Rect(140, y, 1000, 64)
        pygame.draw.rect(surface, ui.C_BG, row, border_radius=8)
        pygame.draw.rect(surface, ui.C_EDGE, row, 1, border_radius=8)
        # Status glyph (not colour-only)
        glyph = {"COMPLETED": "✓", "AVAILABLE": "▶", "IN_PROGRESS": "●", "LOCKED": "◌"}.get(st, "·")
        ui.label(surface, fonts, f"{glyph}  {st}", (160, y + 10), color, "small")
        ui.label(surface, fonts, meta["name"], (320, y + 10), ui.C_TEXT, "body")
        if st == camp.STATUS_LOCKED:
            ui.label(surface, fonts, camp.lock_reason(campaign, mid), (320, y + 36), ui.C_MUTED, "small")
        else:
            missing = []
            for m in meta["kit"]:
                if inventory["stock"].get(m, {}).get("qty", 0) < 1:
                    missing.append(mats.CATALOG[m]["name"])
            kit = "Kit ready" if not missing else "Missing: " + ", ".join(missing[:3])
            ui.label(surface, fonts, f"{meta['short']}  ·  {kit}", (320, y + 36), ui.C_MUTED, "small")
        y += 76

    ui.label(
        surface, fonts,
        f"Research tasks completed: {len(campaign['research_tasks_completed'])}",
        (140, 500),
        ui.C_MUTED,
        "small",
    )
    if campaign.get("reward_log"):
        ui.label(surface, fonts, ui.truncate("Recent: " + campaign["reward_log"][-1], 80), (140, 524), ui.C_MUTED, "small")

    btns = {
        "research": pygame.Rect(140, 580, 200, 40),
        "shop": pygame.Rect(360, 580, 200, 40),
        "close": pygame.Rect(580, 580, 200, 40),
    }
    if campaign.get("campaign_completed"):
        btns["final"] = pygame.Rect(800, 580, 200, 40)
        ui.button(surface, btns["final"], "FINAL REPORT", fonts, mouse_pos, small=True)
    ui.button(surface, btns["research"], "RESEARCH", fonts, mouse_pos, small=True)
    ui.button(surface, btns["shop"], "PROCUREMENT", fonts, mouse_pos, small=True)
    ui.button(surface, btns["close"], "CLOSE", fonts, mouse_pos, small=True)
    return btns


def draw_mission_report(surface, fonts, mouse_pos, campaign: dict, mission_id: str) -> dict:
    ui.dim_backdrop(surface, 160)
    box = pygame.Rect(240, 100, 800, 520)
    ui.panel(surface, box, accent=ui.C_GREEN)
    rec = campaign.get("mission_completion_records", {}).get(mission_id, {})
    meta = camp.MISSION_META.get(mission_id, {})
    ui.header(surface, fonts, box, "MISSION REPORT", meta.get("name", mission_id))
    lines = [
        "STATUS: COMPLETED",
        f"Completed: {rec.get('completed_at', '—')}",
        f"Mission Score awarded: {rec.get('points_awarded', 0)} (once)",
        f"Time left: {rec.get('time_left', '—')}",
        f"Notes: {rec.get('summary', 'Systems restored.')}",
    ]
    for i, line in enumerate(lines):
        ui.centered(surface, fonts, ui.truncate(str(line), 70), (box.centerx, 210 + i * 36), ui.C_TEXT, "body")
    ui.centered(surface, fonts, "Challenge will not restart. Rewards already saved.", (box.centerx, 430), ui.C_MUTED, "small")
    close = pygame.Rect(0, 0, 240, 44)
    close.center = (box.centerx, 520)
    ui.button(surface, close, "RETURN TO BASE", fonts, mouse_pos)
    return {"close": close}


def draw_final_report(surface, fonts, mouse_pos, campaign: dict) -> dict:
    ui.dim_backdrop(surface, 170)
    box = pygame.Rect(200, 80, 880, 560)
    ui.panel(surface, box, accent=ui.C_SIGNAL)
    ui.header(surface, fonts, box, "FINAL MISSION REPORT", "Mars research campaign complete")
    lines = [
        f"Mission Score: {campaign['mission_score']}",
        f"Research Points remaining: {campaign['research_points']} RP",
        f"Missions completed: {len(campaign['completed_missions'])}/3",
        f"Research tasks: {len(campaign['research_tasks_completed'])}",
        f"Campaign seed: {campaign['campaign_seed']}",
        "Communication ONLINE · Power ONLINE · Rover RESCUED",
    ]
    for i, line in enumerate(lines):
        ui.centered(surface, fonts, line, (box.centerx, 200 + i * 36), ui.C_TEXT, "body")
    close = pygame.Rect(0, 0, 240, 44)
    close.center = (box.centerx, 540)
    ui.button(surface, close, "CLOSE", fonts, mouse_pos)
    return {"close": close}


def draw_locked_notice(surface, fonts, mouse_pos, reason: str) -> dict:
    ui.dim_backdrop(surface, 150)
    box = pygame.Rect(320, 230, 640, 260)
    ui.panel(surface, box, accent=ui.C_AMBER)
    ui.centered(surface, fonts, "MISSION LOCKED", (box.centerx, 290), ui.C_AMBER, "title")
    ui.centered(surface, fonts, ui.truncate(reason, 70), (box.centerx, 350), ui.C_TEXT, "body")
    close = pygame.Rect(0, 0, 200, 44)
    close.center = (box.centerx, 420)
    ui.button(surface, close, "BACK", fonts, mouse_pos)
    return {"close": close}
