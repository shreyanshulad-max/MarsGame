"""Research Terminal UI — NASA dataset preview + analysis tasks."""

from __future__ import annotations

import pygame

from systems import campaign as camp
from systems import challenge_ui as ui
from systems import research_data as rdata
from systems import research_tasks as rtasks


def make_ui_state() -> dict:
    return {
        "selected_task": None,
        "selected_option": None,
        "feedback": "",
        "last_reward": "",
        "scroll": 0,
        "show_source": False,
    }


def draw(
    surface,
    fonts,
    mouse_pos,
    campaign: dict,
    ui_state: dict,
) -> dict:
    ui.dim_backdrop(surface, 150)
    box = pygame.Rect(48, 24, 1184, 672)
    ui.panel(surface, box)
    ui.header(
        surface, fonts, box,
        "RESEARCH TERMINAL",
        f"Tier {campaign.get('research_tier', 1)}   ·   {campaign['research_points']} RP",
    )

    manifest = rdata.load_manifest()
    tier = campaign.get("research_tier", 1)
    tasks = rtasks.tasks_for_tier(tier)

    # Task list
    list_box = pygame.Rect(72, 100, 340, 520)
    pygame.draw.rect(surface, ui.C_BG, list_box, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, list_box, 1, border_radius=8)
    ui.label(surface, fonts, "ASSIGNMENTS", (88, 112), ui.C_MUTED, "small")
    task_rects = {}
    y = 140
    for t in tasks:
        done = t["id"] in campaign["research_tasks_completed"]
        r = pygame.Rect(84, y, 316, 44)
        sel = ui_state.get("selected_task") == t["id"]
        pygame.draw.rect(surface, ui.C_SURFACE_2 if sel else ui.C_SURFACE, r, border_radius=6)
        border = ui.C_GREEN if done else (ui.C_SIGNAL if sel else ui.C_EDGE)
        pygame.draw.rect(surface, border, r, 1, border_radius=6)
        mark = "✓" if done else f"T{t['tier']}"
        ui.label(surface, fonts, f"{mark}  {ui.truncate(t['title'], 26)}", (r.x + 10, r.y + 12), ui.C_TEXT, "small")
        task_rects[t["id"]] = r
        y += 50

    # Detail / analysis
    detail = pygame.Rect(432, 100, 772, 520)
    pygame.draw.rect(surface, ui.C_BG, detail, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, detail, 1, border_radius=8)

    option_rects = {}
    submit = pygame.Rect(0, 0, 0, 0)
    source_btn = pygame.Rect(0, 0, 0, 0)
    tid = ui_state.get("selected_task")
    task = rtasks.get_task(tid) if tid else None
    if not task:
        ui.centered(surface, fonts, "Select an assignment", (detail.centerx, 320), ui.C_MUTED, "body")
        ui.centered(surface, fonts, "Analyze NASA browse data — measurements are never invented.", (detail.centerx, 356), ui.C_MUTED, "small")
    else:
        done = task["id"] in campaign["research_tasks_completed"]
        ui.label(surface, fonts, task["title"], (452, 116), ui.C_TEXT, "body")
        item = rdata.get_item(manifest, task["dataset_item"])
        avail = rdata.item_available(item)
        status = "AVAILABLE" if avail else "UNAVAILABLE"
        col = ui.C_GREEN if avail else ui.C_AMBER
        ui.label(surface, fonts, f"Dataset  {status}", (452, 146), col, "small")
        ui.label(surface, fonts, f"Reward  {task['base_rp']} RP", (620, 146), ui.C_SIGNAL, "small")

        # Compact preview
        img = rdata.load_image_surface(item) if item and avail else None
        if img:
            thumb = pygame.transform.smoothscale(img, (240, 136))
            surface.blit(thumb, (452, 176))
        else:
            pygame.draw.rect(surface, ui.C_SURFACE, (452, 176, 240, 136), border_radius=6)
            ui.centered(surface, fonts, "No browse image", (572, 244), ui.C_MUTED, "small")

        cmp_id = task.get("compare_item")
        if cmp_id:
            item2 = rdata.get_item(manifest, cmp_id)
            img2 = rdata.load_image_surface(item2) if rdata.item_available(item2) else None
            if img2:
                thumb2 = pygame.transform.smoothscale(img2, (240, 136))
                surface.blit(thumb2, (712, 176))

        # Source metadata (progressive disclosure)
        source_btn = pygame.Rect(972, 176, 200, 32)
        ui.button(
            surface, source_btn,
            "HIDE SOURCE" if ui_state.get("show_source") else "SOURCE INFO",
            fonts, mouse_pos, small=True,
        )
        if ui_state.get("show_source") and item:
            ui.label(surface, fonts, ui.truncate(f"Product: {item.get('product_id') or 'n/a'}", 48), (452, 324), ui.C_MUTED, "small")
            src = (item.get("source_portal") or item.get("source_url") or "")[:60]
            ui.label(surface, fonts, ui.truncate(f"Source: {src}", 60), (452, 344), ui.C_MUTED, "small")

        num_id = task.get("numeric_item")
        if num_id:
            num = rdata.get_item(manifest, num_id)
            if not rdata.item_available(num):
                ui.label(surface, fonts, "Numeric MOLA profile: UNAVAILABLE (not fabricated)", (452, 368), ui.C_AMBER, "small")

        ui.label(surface, fonts, ui.truncate(task["prompt"], 88), (452, 400), ui.C_TEXT, "small")
        ox = 452
        for key, label in task["options"]:
            r = pygame.Rect(ox, 436, 220, 36)
            sel = ui_state.get("selected_option") == key
            pygame.draw.rect(surface, ui.C_SURFACE_2 if sel else ui.C_SURFACE, r, border_radius=6)
            pygame.draw.rect(surface, ui.C_SIGNAL if sel else ui.C_EDGE, r, 1, border_radius=6)
            ui.centered(surface, fonts, f"{key}) {ui.truncate(label, 18)}", r.center, ui.C_TEXT, "small")
            option_rects[key] = r
            ox += 232

        if done:
            ui.label(surface, fonts, "COMPLETED — RP already awarded.", (452, 500), ui.C_GREEN, "small")
            ui.label(surface, fonts, ui.truncate(task.get("explanation", ""), 70), (452, 528), ui.C_MUTED, "small")
        else:
            submit = pygame.Rect(452, 500, 200, 40)
            ui.button(surface, submit, "SUBMIT", fonts, mouse_pos, accent=True, small=True)
            ui.label(surface, fonts, ui.truncate(f"Hint: {task.get('hint', '')}", 50), (670, 510), ui.C_MUTED, "small")

        if ui_state.get("feedback"):
            ui.label(surface, fonts, ui.truncate(ui_state["feedback"], 70), (452, 560), ui.C_SIGNAL, "small")

    attr = ui.truncate(manifest.get("attribution", ""), 100)
    ui.label(surface, fonts, attr, (72, 636), ui.C_MUTED, "small")

    close = pygame.Rect(520, 640, 240, 36)
    ui.button(surface, close, "CLOSE", fonts, mouse_pos, small=True)
    return {
        "tasks": task_rects,
        "options": option_rects,
        "submit": submit,
        "close": close,
        "source": source_btn,
    }


def handle_event(campaign, inventory, event, ui_state, hit) -> bool:
    """Handle click. Returns True if should close."""
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return False
    pos = event.pos
    if hit["close"].collidepoint(pos):
        return True
    src = hit.get("source")
    if src and src.width > 0 and src.collidepoint(pos):
        ui_state["show_source"] = not ui_state.get("show_source", False)
        return False
    for tid, rect in hit.get("tasks", {}).items():
        if rect.collidepoint(pos):
            ui_state["selected_task"] = tid
            ui_state["selected_option"] = None
            ui_state["feedback"] = ""
            ui_state["show_source"] = False
            return False
    for key, rect in hit.get("options", {}).items():
        if rect.collidepoint(pos):
            ui_state["selected_option"] = key
            return False
    if hit.get("submit") and hit["submit"].width > 0 and hit["submit"].collidepoint(pos):
        tid = ui_state.get("selected_task")
        task = rtasks.get_task(tid) if tid else None
        ans = ui_state.get("selected_option")
        if not task or not ans:
            ui_state["feedback"] = "Choose an option before submitting."
            return False
        if tid in campaign["research_tasks_completed"]:
            ui_state["feedback"] = "Already completed."
            return False
        correct, acc, first = rtasks.grade(task, ans)
        if not correct:
            ui_state["feedback"] = "Not quite — review the imagery/metadata and try again."
            return False
        manifest = rdata.load_manifest()
        item = rdata.get_item(manifest, task["dataset_item"])
        if task["id"] not in ("res_mola_elevation", "res_mola_honesty") and not rdata.item_available(item):
            ui_state["feedback"] = "Dataset browse image unavailable — cannot complete this analysis yet."
            return False
        result = camp.award_research(campaign, tid, task["base_rp"], acc, first)
        ui_state["feedback"] = result["message"] + " · " + task.get("explanation", "")[:40]
        ui_state["last_reward"] = ", ".join(result.get("breakdown", []))
        return False
    return False
