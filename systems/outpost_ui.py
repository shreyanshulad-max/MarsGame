"""Outpost dashboard — life support, radiation, power, food (dedicated panel)."""

from __future__ import annotations

import pygame

from systems import challenge_ui as ui
from systems import outpost as op


def draw_dashboard(surface, fonts, mouse_pos, campaign: dict) -> dict:
    state = op.ensure_outpost(campaign)
    ui.dim_backdrop(surface, 160)
    box = pygame.Rect(80, 36, 1120, 648)
    ui.panel(surface, box)
    ui.header(surface, fonts, box, "OUTPOST SYSTEMS", "Simulation indices — not NASA engineering specs")

    # Four panels
    panels = [
        ("LIFE SUPPORT", state["life_support"], pygame.Rect(110, 120, 500, 200)),
        ("RADIATION PROTECTION", state["radiation"], pygame.Rect(650, 120, 500, 200)),
        ("POWER MANAGEMENT", state["power"], pygame.Rect(110, 340, 500, 220)),
        ("FOOD PRODUCTION", state["food"], pygame.Rect(650, 340, 500, 220)),
    ]
    buttons = {}
    for title, data, rect in panels:
        pygame.draw.rect(surface, ui.C_BG, rect, border_radius=10)
        pygame.draw.rect(surface, ui.C_EDGE, rect, 1, border_radius=10)
        ui.label(surface, fonts, title, (rect.x + 16, rect.y + 12), ui.C_SIGNAL, "small")
        if title.startswith("LIFE"):
            ui.label(surface, fonts, f"Oxygen circulation  {int(data['oxygen_circulation'])}", (rect.x + 16, rect.y + 50), ui.C_TEXT, "body")
            ui.label(surface, fonts, f"Habitat stability   {int(data['habitat_stability'])}", (rect.x + 16, rect.y + 84), ui.C_TEXT, "body")
            warn = data.get("warning") or ("Power OK" if data.get("power_ok") else "Needs power")
            ui.label(surface, fonts, ui.truncate(warn, 48), (rect.x + 16, rect.y + 130), ui.C_AMBER if data.get("warning") else ui.C_MUTED, "small")
        elif title.startswith("RAD"):
            ui.label(surface, fonts, f"Config  {data['shielding_config']}", (rect.x + 16, rect.y + 50), ui.C_TEXT, "body")
            ui.label(surface, fonts, f"Protection index  {int(data['protection_index'])} (sim)", (rect.x + 16, rect.y + 84), ui.C_TEXT, "body")
            ui.label(surface, fonts, f"Exposure risk     {int(data['exposure_risk_index'])} (sim)", (rect.x + 16, rect.y + 118), ui.C_TEXT, "body")
            ui.label(surface, fonts, ui.truncate(data.get("notes", ""), 48), (rect.x + 16, rect.y + 152), ui.C_MUTED, "small")
            for i, (cid, lab) in enumerate((("baseline", "BASE"), ("polymer", "POLY"), ("regolith_sim", "REGOLITH"))):
                r = pygame.Rect(rect.x + 16 + i * 150, rect.bottom - 44, 140, 32)
                ui.button(surface, r, lab, fonts, mouse_pos, small=True, accent=data["shielding_config"] == cid)
                buttons[f"shield_{cid}"] = r
        elif title.startswith("POWER"):
            budget = op.effective_budget(state)
            total = op.allocation_total(state)
            ui.label(surface, fonts, f"Budget {budget}  ·  Used {total}  ·  Free {budget - total}", (rect.x + 16, rect.y + 44), ui.C_TEXT, "body")
            y = rect.y + 78
            for sys_id, val in state["power"]["allocation"].items():
                need = op.MIN_REQUIREMENTS.get(sys_id, 0)
                ok = val >= need
                ui.label(surface, fonts, f"{sys_id}: {val} (min {need})", (rect.x + 16, y), ui.C_GREEN if ok else ui.C_AMBER, "small")
                minus = pygame.Rect(rect.x + 280, y - 2, 36, 24)
                plus = pygame.Rect(rect.x + 322, y - 2, 36, 24)
                ui.button(surface, minus, "−", fonts, mouse_pos, small=True)
                ui.button(surface, plus, "+", fonts, mouse_pos, small=True)
                buttons[f"pwr_minus_{sys_id}"] = minus
                buttons[f"pwr_plus_{sys_id}"] = plus
                y += 26
            conf = pygame.Rect(rect.x + 16, rect.bottom - 40, 200, 32)
            ui.button(surface, conf, "CONFIRM POWER", fonts, mouse_pos, small=True, accent=True)
            buttons["confirm_power"] = conf
            dust = pygame.Rect(rect.x + 230, rect.bottom - 40, 200, 32)
            ui.button(surface, dust, "TOGGLE DUST", fonts, mouse_pos, small=True)
            buttons["toggle_dust"] = dust
        else:
            ui.label(surface, fonts, f"Status  {data['status']}", (rect.x + 16, rect.y + 48), ui.C_TEXT, "body")
            ui.label(surface, fonts, f"Growth  {int(data['growth'])}%", (rect.x + 16, rect.y + 82), ui.C_TEXT, "body")
            ui.label(surface, fonts, f"Water {int(data['water'])}  ·  Nutrients {int(data['nutrients'])}", (rect.x + 16, rect.y + 116), ui.C_MUTED, "small")
            ui.label(
                surface, fonts,
                "Lighting power: " + ("OK" if data.get("lighting_power_ok") else "NEED ≥10 to food"),
                (rect.x + 16, rect.y + 148),
                ui.C_GREEN if data.get("lighting_power_ok") else ui.C_AMBER,
                "small",
            )
            harv = pygame.Rect(rect.x + 16, rect.bottom - 40, 160, 32)
            refill = pygame.Rect(rect.x + 190, rect.bottom - 40, 160, 32)
            ui.button(surface, harv, "HARVEST", fonts, mouse_pos, small=True, accent=data.get("growth", 0) >= 100)
            ui.button(surface, refill, "REFILL", fonts, mouse_pos, small=True)
            buttons["harvest"] = harv
            buttons["refill"] = refill

    close = pygame.Rect(520, 640, 240, 36)
    ui.button(surface, close, "CLOSE", fonts, mouse_pos, small=True)
    buttons["close"] = close
    return buttons


def handle_click(campaign: dict, hit: dict, pos) -> tuple[bool, str]:
    """Returns (should_close, message)."""
    state = op.ensure_outpost(campaign)
    if hit.get("close") and hit["close"].collidepoint(pos):
        return True, ""
    for cid in ("baseline", "polymer", "regolith_sim"):
        key = f"shield_{cid}"
        if hit.get(key) and hit[key].collidepoint(pos):
            ok, msg = op.set_shielding(state, cid)
            return False, msg
    for sys_id in list(state["power"]["allocation"].keys()):
        if hit.get(f"pwr_minus_{sys_id}") and hit[f"pwr_minus_{sys_id}"].collidepoint(pos):
            ok, msg = op.adjust_allocation(state, sys_id, -5)
            return False, msg
        if hit.get(f"pwr_plus_{sys_id}") and hit[f"pwr_plus_{sys_id}"].collidepoint(pos):
            ok, msg = op.adjust_allocation(state, sys_id, 5)
            return False, msg
    if hit.get("confirm_power") and hit["confirm_power"].collidepoint(pos):
        ok, msg = op.confirm_allocation(state)
        return False, msg
    if hit.get("toggle_dust") and hit["toggle_dust"].collidepoint(pos):
        op.apply_dust_event(state, not state["power"].get("dust_event"))
        return False, "Dust event toggled."
    if hit.get("harvest") and hit["harvest"].collidepoint(pos):
        ok, msg = op.harvest_crop(state)
        return False, msg
    if hit.get("refill") and hit["refill"].collidepoint(pos):
        op.refill_greenhouse(state)
        return False, "Greenhouse water/nutrients refilled."
    return False, ""
