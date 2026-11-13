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
    }


def draw(
    surface,
    fonts,
    mouse_pos,
    campaign: dict,
    ui_state: dict,
) -> dict:
    ui.dim_backdrop(surface, 165)
    box = pygame.Rect(40, 20, 1200, 680)
    ui.panel(surface, box)
    ui.header(
        surface, fonts, box,
        "RESEARCH TERMINAL",
        f"Tier {campaign.get('research_tier', 1)}  ·  {campaign['research_points']} RP  ·  NASA local data pack",
    )

    manifest = rdata.load_manifest()
    tier = campaign.get("research_tier", 1)
    tasks = rtasks.tasks_for_tier(tier)

    # Task list
    list_box = pygame.Rect(60, 120, 360, 480)
    pygame.draw.rect(surface, (32, 20, 14), list_box, border_radius=10)
    pygame.draw.rect(surface, ui.C_CYAN, list_box, 2, border_radius=10)
    ui.label(surface, fonts, "RESEARCH TASKS", (80, 135), ui.C_CYAN, "small")
    task_rects = {}
    y = 170
    for t in tasks:
        done = t["id"] in campaign["research_tasks_completed"]
        r = pygame.Rect(75, y, 330, 48)
        sel = ui_state.get("selected_task") == t["id"]
        pygame.draw.rect(surface, (48, 32, 20) if sel else (38, 24, 16), r, border_radius=8)
        border = ui.C_GREEN if done else (ui.C_CYAN if sel else ui.C_EDGE)
        pygame.draw.rect(surface, border, r, 2, border_radius=8)
        mark = "[DONE]" if done else f"T{t['tier']}"
        ui.label(surface, fonts, f"{mark} {t['title'][:28]}", (r.x + 10, r.y + 14), ui.C_TEXT, "small")
        task_rects[t["id"]] = r
        y += 56

    # Detail / analysis
    detail = pygame.Rect(440, 120, 780, 480)
    pygame.draw.rect(surface, (32, 20, 14), detail, border_radius=10)
    pygame.draw.rect(surface, ui.C_EDGE, detail, 2, border_radius=10)

    option_rects = {}
    submit = pygame.Rect(0, 0, 0, 0)
    tid = ui_state.get("selected_task")
    task = rtasks.get_task(tid) if tid else None
    if not task:
        ui.centered(surface, fonts, "Select a research task", (detail.centerx, 300), ui.C_MUTED, "body")
        ui.centered(surface, fonts, "Analyze NASA browse data — do not invent measurements.", (detail.centerx, 340), ui.C_MUTED, "small")
    else:
        ui.label(surface, fonts, task["title"], (460, 135), ui.C_TEXT, "body")
        item = rdata.get_item(manifest, task["dataset_item"])
        avail = rdata.item_available(item)
        status = "AVAILABLE" if avail else "UNAVAILABLE"
        col = ui.C_GREEN if avail else ui.C_RED
        ui.label(surface, fonts, f"Dataset: {task['dataset_item']} [{status}]", (460, 165), col, "small")
        if item:
            ui.label(surface, fonts, f"Product: {item.get('product_id') or 'n/a'}", (460, 188), ui.C_MUTED, "small")
            src = (item.get("source_portal") or item.get("source_url") or "")[:70]
            ui.label(surface, fonts, f"Source: {src}", (460, 210), ui.C_MUTED, "small")

        # Image previews
        img = rdata.load_image_surface(item) if item and avail else None
        if img:
            thumb = pygame.transform.smoothscale(img, (280, 160))
            surface.blit(thumb, (460, 240))
        else:
            pygame.draw.rect(surface, (20, 12, 10), (460, 240, 280, 160), border_radius=8)
            ui.centered(surface, fonts, "No local browse image", (600, 320), ui.C_RED, "small")

        cmp_id = task.get("compare_item")
        if cmp_id:
            item2 = rdata.get_item(manifest, cmp_id)
            img2 = rdata.load_image_surface(item2) if rdata.item_available(item2) else None
            if img2:
                thumb2 = pygame.transform.smoothscale(img2, (280, 160))
                surface.blit(thumb2, (760, 240))
            else:
                pygame.draw.rect(surface, (20, 12, 10), (760, 240, 280, 160), border_radius=8)

        # Numeric honesty badge
        num_id = task.get("numeric_item")
        if num_id:
            num = rdata.get_item(manifest, num_id)
            if not rdata.item_available(num):
                ui.label(
                    surface, fonts,
                    "Numeric MOLA profile: UNAVAILABLE (not fabricated)",
                    (460, 410), ui.C_AMBER, "small",
                )

        ui.label(surface, fonts, task["prompt"][:90], (460, 435), ui.C_TEXT, "small")
        ox = 460
        for key, label in task["options"]:
            r = pygame.Rect(ox, 470, 230, 40)
            sel = ui_state.get("selected_option") == key
            pygame.draw.rect(surface, (45, 28, 18) if sel else (30, 18, 12), r, border_radius=8)
            pygame.draw.rect(surface, ui.C_CYAN if sel else ui.C_EDGE, r, 2, border_radius=8)
            ui.centered(surface, fonts, f"{key}) {label[:22]}", r.center, ui.C_TEXT, "small")
            option_rects[key] = r
            ox += 245

        done = task["id"] in campaign["research_tasks_completed"]
        if done:
            ui.label(surface, fonts, "COMPLETED — RP already awarded.", (460, 530), ui.C_GREEN, "body")
            ui.label(surface, fonts, task.get("explanation", "")[:80], (460, 560), ui.C_MUTED, "small")
        else:
            submit = pygame.Rect(460, 530, 220, 44)
            ui.button(surface, submit, "SUBMIT ANALYSIS", fonts, mouse_pos, small=True)
            ui.label(surface, fonts, f"Hint: {task.get('hint', '')[:70]}", (700, 540), ui.C_AMBER, "small")

        if ui_state.get("feedback"):
            ui.label(surface, fonts, ui_state["feedback"][:80], (460, 585), ui.C_CYAN, "small")

    # Attribution footer
    attr = manifest.get("attribution", "")[:110]
    ui.label(surface, fonts, attr, (60, 620), ui.C_MUTED, "small")

    close = pygame.Rect(520, 650, 240, 36)
    ui.button(surface, close, "CLOSE", fonts, mouse_pos, small=True)
    return {"tasks": task_rects, "options": option_rects, "submit": submit, "close": close}


def handle_event(campaign, inventory, event, ui_state, hit) -> bool:
    """Handle click. Returns True if should close."""
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return False
    pos = event.pos
    if hit["close"].collidepoint(pos):
        return True
    for tid, rect in hit.get("tasks", {}).items():
        if rect.collidepoint(pos):
            ui_state["selected_task"] = tid
            ui_state["selected_option"] = None
            ui_state["feedback"] = ""
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
        # Require dataset availability for image tasks (except honesty tasks about unavailability)
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
