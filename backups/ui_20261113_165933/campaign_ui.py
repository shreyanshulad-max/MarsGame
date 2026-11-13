"""Campaign dashboard, mission report, and final report panels."""

from __future__ import annotations

import pygame

from systems import campaign as camp
from systems import challenge_ui as ui
from systems import materials as mats
from systems import procurement as proc


def draw_dashboard(surface, fonts, mouse_pos, campaign: dict, inventory: dict) -> dict:
    ui.dim_backdrop(surface, 170)
    box = pygame.Rect(100, 40, 1080, 640)
    ui.panel(surface, box, accent=ui.C_CYAN)
    ui.header(
        surface, fonts, box,
        "CAMPAIGN DASHBOARD",
        f"Stage: {campaign.get('current_campaign_stage')}  ·  Seed {campaign.get('campaign_seed')}",
    )
    ui.objective_bar(
        surface, fonts,
        f"Mission Score {campaign['mission_score']}  |  Research Points {campaign['research_points']} RP  |  Tier {campaign.get('research_tier', 1)}",
        y=110,
    )

    y = 160
    for mid in camp.MISSION_ORDER:
        meta = camp.MISSION_META[mid]
        st = camp.mission_status(campaign, mid)
        color = {
            camp.STATUS_COMPLETED: ui.C_GREEN,
            camp.STATUS_AVAILABLE: ui.C_AMBER,
            camp.STATUS_IN_PROGRESS: ui.C_CYAN,
            camp.STATUS_LOCKED: ui.C_RED,
        }.get(st, ui.C_MUTED)
        ui.label(surface, fonts, f"[{st}] {meta['name']}", (140, y), color, "body")
        if st == camp.STATUS_LOCKED:
            ui.label(surface, fonts, camp.lock_reason(campaign, mid), (160, y + 26), ui.C_MUTED, "small")
        else:
            # kit status
            missing = []
            for m in meta["kit"]:
                if inventory["stock"].get(m, {}).get("qty", 0) < 1:
                    missing.append(mats.CATALOG[m]["name"])
            kit = "Kit ready" if not missing else "Missing: " + ", ".join(missing[:3])
            ui.label(surface, fonts, f"{meta['short']}  ·  {kit}", (160, y + 26), ui.C_MUTED, "small")
        y += 70

    ui.label(surface, fonts, "Research tasks completed: " + str(len(campaign["research_tasks_completed"])), (140, 500), ui.C_TEXT, "small")
    if campaign.get("reward_log"):
        ui.label(surface, fonts, "Recent: " + campaign["reward_log"][-1][:70], (140, 530), ui.C_CYAN, "small")

    btns = {
        "research": pygame.Rect(140, 580, 220, 44),
        "shop": pygame.Rect(380, 580, 220, 44),
        "close": pygame.Rect(620, 580, 220, 44),
    }
    if campaign.get("campaign_completed"):
        btns["final"] = pygame.Rect(860, 580, 220, 44)
        ui.button(surface, btns["final"], "FINAL REPORT", fonts, mouse_pos, small=True)
    ui.button(surface, btns["research"], "RESEARCH", fonts, mouse_pos, small=True)
    ui.button(surface, btns["shop"], "PROCUREMENT", fonts, mouse_pos, small=True)
    ui.button(surface, btns["close"], "CLOSE", fonts, mouse_pos, small=True)
    return btns


def draw_mission_report(surface, fonts, mouse_pos, campaign: dict, mission_id: str) -> dict:
    ui.dim_backdrop(surface, 170)
    box = pygame.Rect(220, 80, 840, 560)
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
        ui.centered(surface, fonts, line, (box.centerx, 220 + i * 40), ui.C_TEXT, "body")
    ui.centered(surface, fonts, "Challenge will not restart. Rewards already saved.", (box.centerx, 460), ui.C_AMBER, "small")
    close = pygame.Rect(0, 0, 260, 48)
    close.center = (box.centerx, 540)
    ui.button(surface, close, "RETURN TO BASE", fonts, mouse_pos)
    return {"close": close}


def draw_final_report(surface, fonts, mouse_pos, campaign: dict) -> dict:
    ui.dim_backdrop(surface, 180)
    box = pygame.Rect(180, 60, 920, 600)
    ui.panel(surface, box, accent=ui.C_CYAN)
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
        ui.centered(surface, fonts, line, (box.centerx, 200 + i * 40), ui.C_TEXT, "body")
    close = pygame.Rect(0, 0, 260, 48)
    close.center = (box.centerx, 560)
    ui.button(surface, close, "CLOSE", fonts, mouse_pos)
    return {"close": close}


def draw_locked_notice(surface, fonts, mouse_pos, reason: str) -> dict:
    ui.dim_backdrop(surface, 160)
    box = pygame.Rect(300, 220, 680, 280)
    ui.panel(surface, box, accent=ui.C_RED)
    ui.centered(surface, fonts, "MISSION LOCKED", (box.centerx, 280), ui.C_RED, "title")
    ui.centered(surface, fonts, reason[:70], (box.centerx, 340), ui.C_TEXT, "body")
    close = pygame.Rect(0, 0, 240, 48)
    close.center = (box.centerx, 420)
    ui.button(surface, close, "BACK", fonts, mouse_pos)
    return {"close": close}
