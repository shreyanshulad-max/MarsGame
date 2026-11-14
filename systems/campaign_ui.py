"""Campaign dashboard, title actions, mission report/replay, new-campaign confirm."""

from __future__ import annotations

import pygame

from systems import campaign as camp
from systems import challenge_ui as ui
from systems import materials as mats
from systems import research_tasks as rtasks
from systems import savegame


def draw_title_menu(surface, fonts, mouse_pos, has_save: bool, campaign: dict | None, recovery: dict | None) -> dict:
    """Title overlay buttons — Continue / New / Records / Quit."""
    btns = {}
    cx = surface.get_width() // 2
    y = 360
    if recovery:
        ui.centered(surface, fonts, "SAVE RECOVERY NEEDED", (cx, 320), ui.C_AMBER, "body")
        ui.centered(
            surface, fonts,
            ui.truncate(recovery.get("message", "Could not load campaign save."), 70),
            (cx, 348), ui.C_MUTED, "small",
        )
        y = 390

    if has_save and campaign and not recovery:
        if campaign.get("campaign_completed"):
            r = pygame.Rect(0, 0, 300, 48)
            r.center = (cx, y)
            ui.button(surface, r, "CAMPAIGN COMPLETED", fonts, mouse_pos, accent=True)
            btns["completed"] = r
            y += 58
            r = pygame.Rect(0, 0, 300, 44)
            r.center = (cx, y)
            ui.button(surface, r, "REVIEW FINAL REPORT", fonts, mouse_pos, small=True)
            btns["final"] = r
            y += 52
            r = pygame.Rect(0, 0, 300, 44)
            r.center = (cx, y)
            ui.button(surface, r, "REPLAY MISSIONS", fonts, mouse_pos, small=True)
            btns["records"] = r
            y += 52
        else:
            r = pygame.Rect(0, 0, 300, 52)
            r.center = (cx, y)
            ui.button(surface, r, "CONTINUE CAMPAIGN", fonts, mouse_pos, accent=True)
            btns["continue"] = r
            y += 60
            r = pygame.Rect(0, 0, 300, 44)
            r.center = (cx, y)
            ui.button(surface, r, "MISSION RECORDS", fonts, mouse_pos, small=True)
            btns["records"] = r
            y += 52

        r = pygame.Rect(0, 0, 300, 44)
        r.center = (cx, y)
        ui.button(surface, r, "NEW CAMPAIGN", fonts, mouse_pos, small=True)
        btns["new"] = r
        y += 52
    else:
        r = pygame.Rect(0, 0, 300, 52)
        r.center = (cx, y)
        ui.button(surface, r, "START NEW CAMPAIGN", fonts, mouse_pos, accent=True)
        btns["new"] = r
        y += 60

    r = pygame.Rect(0, 0, 300, 44)
    r.center = (cx, y)
    ui.button(surface, r, "QUIT", fonts, mouse_pos, small=True)
    btns["quit"] = r
    return btns


def draw_new_campaign_confirm(surface, fonts, mouse_pos) -> dict:
    ui.dim_backdrop(surface, 180)
    box = pygame.Rect(260, 120, 760, 480)
    ui.panel(surface, box, accent=ui.C_AMBER)
    ui.header(surface, fonts, box, "START NEW CAMPAIGN?", "This archives the current campaign")
    lines = [
        "Existing progress will be archived (not deleted).",
        "Mission completion will reset.",
        "Research tasks and Research Points will reset.",
        "Mission Score and inventory will reset.",
        "Material caches will receive a new random layout.",
        "Previous campaign reports remain in the archive.",
    ]
    for i, line in enumerate(lines):
        ui.centered(surface, fonts, line, (box.centerx, 220 + i * 32), ui.C_TEXT, "small")
    confirm = pygame.Rect(0, 0, 220, 44)
    cancel = pygame.Rect(0, 0, 220, 44)
    confirm.center = (box.centerx - 130, 540)
    cancel.center = (box.centerx + 130, 540)
    ui.button(surface, confirm, "CONFIRM", fonts, mouse_pos, accent=True)
    ui.button(surface, cancel, "CANCEL", fonts, mouse_pos)
    return {"confirm": confirm, "cancel": cancel}


def draw_dashboard(surface, fonts, mouse_pos, campaign: dict, inventory: dict) -> dict:
    ui.dim_backdrop(surface, 160)
    box = pygame.Rect(100, 48, 1080, 624)
    ui.panel(surface, box)
    y = ui.header(
        surface, fonts, box,
        "CAMPAIGN",
        f"Stage {campaign.get('current_campaign_stage')}   ·   Seed {campaign.get('campaign_seed')}",
    )

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
        glyph = {"COMPLETED": "✓", "AVAILABLE": "▶", "IN_PROGRESS": "●", "LOCKED": "◌"}.get(st, "·")
        ui.label(surface, fonts, f"{glyph}  {st}", (160, y + 10), color, "small")
        ui.label(surface, fonts, meta["name"], (320, y + 10), ui.C_TEXT, "body")
        if st == camp.STATUS_LOCKED:
            ui.label(surface, fonts, camp.lock_reason(campaign, mid), (320, y + 36), ui.C_MUTED, "small")
        else:
            ready = camp.mission_readiness(campaign, inventory["stock"], mid)
            if st == camp.STATUS_COMPLETED:
                ui.label(surface, fonts, "Completed — open station for report / replay", (320, y + 36), ui.C_MUTED, "small")
            elif ready["can_start"]:
                ui.label(surface, fonts, "Prepared — ready to start at station", (320, y + 36), ui.C_GREEN, "small")
            else:
                msg = ready["reasons"][0] if ready["reasons"] else "Preparation incomplete"
                ui.label(surface, fonts, ui.truncate(msg, 70), (320, y + 36), ui.C_MUTED, "small")
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
        "research": pygame.Rect(120, 580, 160, 40),
        "shop": pygame.Rect(300, 580, 160, 40),
        "outpost": pygame.Rect(480, 580, 160, 40),
        "records": pygame.Rect(660, 580, 160, 40),
        "close": pygame.Rect(840, 580, 160, 40),
    }
    if campaign.get("campaign_completed"):
        btns["final"] = pygame.Rect(1000, 580, 140, 40)
        ui.button(surface, btns["final"], "FINAL", fonts, mouse_pos, small=True)
        btns["new"] = pygame.Rect(1000, 520, 140, 40)
        ui.button(surface, btns["new"], "NEW", fonts, mouse_pos, small=True)
    ui.button(surface, btns["research"], "RESEARCH", fonts, mouse_pos, small=True)
    ui.button(surface, btns["shop"], "PROCUREMENT", fonts, mouse_pos, small=True)
    ui.button(surface, btns["outpost"], "OUTPOST", fonts, mouse_pos, small=True)
    ui.button(surface, btns["records"], "RECORDS", fonts, mouse_pos, small=True)
    ui.button(surface, btns["close"], "CLOSE", fonts, mouse_pos, small=True)
    return btns


def draw_mission_prep(surface, fonts, mouse_pos, campaign: dict, inventory: dict, mission_id: str) -> dict:
    """Shown when player opens an available mission that is not yet prepared."""
    ui.dim_backdrop(surface, 160)
    box = pygame.Rect(180, 60, 920, 600)
    ui.panel(surface, box)
    meta = camp.MISSION_META.get(mission_id, {})
    ready = camp.mission_readiness(campaign, inventory["stock"], mission_id)
    ui.header(surface, fonts, box, meta.get("name", mission_id), "Mission preparation")

    ui.label(surface, fonts, "RESEARCH", (220, 140), ui.C_MUTED, "small")
    y = 168
    for tid in camp.CLEARANCE_TASKS.get(mission_id, []):
        task = rtasks.get_task(tid)
        done = tid in campaign.get("research_tasks_completed", [])
        mark = "✓" if done else "○"
        title = task["title"] if task else tid
        ui.label(surface, fonts, f"{mark}  {title}", (220, y), ui.C_GREEN if done else ui.C_TEXT, "small")
        y += 28

    ui.label(surface, fonts, "MATERIALS", (220, y + 12), ui.C_MUTED, "small")
    y += 40
    for mid, info in ready.get("materials", {}).items():
        line = f"{info['name']}: {info['owned']}/{info['required']}  (purchased {info['purchased']}, need {info['remaining']})"
        ui.label(surface, fonts, line, (220, y), ui.C_GREEN if info["remaining"] == 0 else ui.C_TEXT, "small")
        y += 28

    for i, reason in enumerate(ready.get("reasons") or []):
        ui.label(surface, fonts, ui.truncate(reason, 80), (220, 480 + i * 22), ui.C_AMBER, "small")

    start = pygame.Rect(0, 0, 0, 0)
    if ready["can_start"]:
        start = pygame.Rect(0, 0, 240, 44)
        start.center = (box.centerx - 130, 600)
        ui.button(surface, start, "START MISSION", fonts, mouse_pos, accent=True)
    back = pygame.Rect(0, 0, 240, 44)
    back.center = (box.centerx + (130 if ready["can_start"] else 0), 600)
    ui.button(surface, back, "RETURN TO BASE", fonts, mouse_pos)
    return {"start": start, "close": back, "can_start": ready["can_start"]}


def draw_mission_report(surface, fonts, mouse_pos, campaign: dict, mission_id: str) -> dict:
    ui.dim_backdrop(surface, 160)
    box = pygame.Rect(200, 80, 880, 560)
    ui.panel(surface, box, accent=ui.C_GREEN)
    rec = (
        campaign.get("mission_reports")
        or campaign.get("mission_completion_records")
        or {}
    ).get(mission_id, {})
    meta = camp.MISSION_META.get(mission_id, {})
    ui.header(surface, fonts, box, "MISSION REPORT", meta.get("name", mission_id))
    lines = [
        "STATUS: COMPLETED",
        f"Completed: {rec.get('completed_at', '—')}",
        f"Mission Score awarded: {rec.get('points_awarded', 0)} (once)",
        f"Materials used: {', '.join(rec.get('materials_used') or meta.get('kit', []))}",
        f"Research: {len(rec.get('research_discoveries') or camp.CLEARANCE_TASKS.get(mission_id, []))} clearance tasks",
        f"Notes: {rec.get('summary', 'Systems restored.')}",
        f"Time left: {rec.get('time_left', '—')}",
    ]
    for i, line in enumerate(lines):
        ui.centered(surface, fonts, ui.truncate(str(line), 78), (box.centerx, 180 + i * 32), ui.C_TEXT, "body")
    ui.centered(
        surface, fonts,
        "Review only — campaign materials are not consumed.",
        (box.centerx, 420),
        ui.C_MUTED,
        "small",
    )
    replay = pygame.Rect(0, 0, 220, 44)
    close = pygame.Rect(0, 0, 220, 44)
    replay.center = (box.centerx - 130, 520)
    close.center = (box.centerx + 130, 520)
    ui.button(surface, replay, "REPLAY MISSION", fonts, mouse_pos, accent=True)
    ui.button(surface, close, "RETURN TO BASE", fonts, mouse_pos)
    return {"replay": replay, "close": close}


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
    close = pygame.Rect(0, 0, 200, 44)
    newc = pygame.Rect(0, 0, 200, 44)
    close.center = (box.centerx - 120, 540)
    newc.center = (box.centerx + 120, 540)
    ui.button(surface, close, "CLOSE", fonts, mouse_pos)
    ui.button(surface, newc, "NEW CAMPAIGN", fonts, mouse_pos, accent=True)
    return {"close": close, "new": newc}


def draw_mission_records(surface, fonts, mouse_pos, campaign: dict | None) -> dict:
    ui.dim_backdrop(surface, 160)
    box = pygame.Rect(180, 70, 920, 580)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "MISSION RECORDS", "Completed missions and archive")
    y = 150
    if campaign:
        for mid in camp.MISSION_ORDER:
            meta = camp.MISSION_META[mid]
            st = camp.mission_status(campaign, mid)
            rec = (campaign.get("mission_reports") or {}).get(mid) or (
                campaign.get("mission_completion_records") or {}
            ).get(mid)
            if st == camp.STATUS_COMPLETED and rec:
                ui.label(surface, fonts, f"✓  {meta['name']}  ·  +{rec.get('points_awarded', 0)} MS", (220, y), ui.C_GREEN, "body")
                ui.label(surface, fonts, f"   {rec.get('completed_at', '')}  ·  {rec.get('summary', '')[:50]}", (220, y + 26), ui.C_MUTED, "small")
            else:
                ui.label(surface, fonts, f"○  {meta['name']}  ·  {st}", (220, y), ui.C_MUTED, "body")
            y += 64
    archive = savegame.load_archive()
    ui.label(surface, fonts, f"Archived campaigns: {len(archive)}", (220, 520), ui.C_MUTED, "small")
    if archive:
        last = archive[-1]
        ui.label(
            surface, fonts,
            ui.truncate(
                f"Last archive: score {last.get('final_mission_score')} · {last.get('completion_date')}",
                70,
            ),
            (220, 548),
            ui.C_MUTED,
            "small",
        )
    close = pygame.Rect(0, 0, 240, 44)
    close.center = (box.centerx, 600)
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


def draw_replay_banner(surface, fonts) -> None:
    bar = pygame.Rect(0, 0, surface.get_width(), 28)
    pygame.draw.rect(surface, (40, 28, 12), bar)
    ui.centered(surface, fonts, "PRACTICE / REPLAY — no campaign rewards", (bar.centerx, 14), ui.C_AMBER, "small")
