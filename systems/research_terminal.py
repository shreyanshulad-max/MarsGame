"""Research Terminal UI — NASA dataset preview + interactive analysis tasks."""

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
        "hint_used": False,
        "marker_pos": None,  # normalized (x,y) in image
        "image_rect": None,
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
    camp.refresh_research_clearance(campaign)
    tier = campaign.get("research_tier", 1)
    active = camp.active_mission_id(campaign)
    clearance = camp.research_clearance_granted(campaign, active) if active else False
    ui.header(
        surface, fonts, box,
        "RESEARCH TERMINAL",
        f"Tier {tier}   ·   {campaign['research_points']} RP   ·   Clearance {'READY' if clearance else 'INCOMPLETE'}",
    )

    manifest = rdata.load_manifest()
    # Show tasks for unlocked tiers, grouped; prefer current mission tier tasks first
    tasks = rtasks.tasks_for_tier(tier)

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
        if y > 580:
            break

    detail = pygame.Rect(432, 100, 772, 520)
    pygame.draw.rect(surface, ui.C_BG, detail, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, detail, 1, border_radius=8)

    option_rects = {}
    hotspot_rects = {}
    submit = pygame.Rect(0, 0, 0, 0)
    source_btn = pygame.Rect(0, 0, 0, 0)
    hint_btn = pygame.Rect(0, 0, 0, 0)
    image_rect = None
    tid = ui_state.get("selected_task")
    task = rtasks.get_task(tid) if tid else None
    if not task:
        ui.centered(surface, fonts, "Select an assignment", (detail.centerx, 300), ui.C_MUTED, "body")
        ui.centered(
            surface, fonts,
            "Complete all three tier tasks for procurement clearance.",
            (detail.centerx, 336),
            ui.C_MUTED,
            "small",
        )
    else:
        done = task["id"] in campaign["research_tasks_completed"]
        ui.label(surface, fonts, task["title"], (452, 110), ui.C_TEXT, "body")
        item = rdata.get_item(manifest, task["dataset_item"])
        avail = rdata.item_available(item)
        needs = task.get("requires_dataset", False)
        status = "AVAILABLE" if avail else "UNAVAILABLE"
        col = ui.C_GREEN if avail else ui.C_AMBER
        ui.label(surface, fonts, f"Dataset  {status}", (452, 138), col, "small")
        ui.label(surface, fonts, f"Reward  {task['base_rp']} RP", (620, 138), ui.C_SIGNAL, "small")
        ui.label(surface, fonts, ui.truncate(task.get("intro", ""), 90), (452, 160), ui.C_MUTED, "small")

        img = rdata.load_image_surface(item) if item and avail else None
        cmp_id = task.get("compare_item")
        img2 = None
        if cmp_id:
            item2 = rdata.get_item(manifest, cmp_id)
            img2 = rdata.load_image_surface(item2) if rdata.item_available(item2) else None

        # Preview / interaction canvas
        image_rect = pygame.Rect(452, 188, 360, 160)
        pygame.draw.rect(surface, ui.C_SURFACE, image_rect, border_radius=6)
        if img and img2 and task.get("interaction") in ("image_pick", "route_compare"):
            half = pygame.Rect(image_rect.x, image_rect.y, image_rect.w // 2 - 4, image_rect.h)
            half2 = pygame.Rect(image_rect.centerx + 2, image_rect.y, image_rect.w // 2 - 4, image_rect.h)
            surface.blit(pygame.transform.smoothscale(img, half.size), half.topleft)
            surface.blit(pygame.transform.smoothscale(img2, half2.size), half2.topleft)
            pygame.draw.rect(surface, ui.C_EDGE, half, 1)
            pygame.draw.rect(surface, ui.C_EDGE, half2, 1)
        elif img:
            thumb = pygame.transform.smoothscale(img, image_rect.size)
            surface.blit(thumb, image_rect.topleft)
            # Marker overlay
            if task.get("interaction") == "marker" and ui_state.get("marker_pos"):
                mx, my = ui_state["marker_pos"]
                px = image_rect.x + int(mx * image_rect.w)
                py = image_rect.y + int(my * image_rect.h)
                pygame.draw.circle(surface, ui.C_MARS, (px, py), 8, 2)
        else:
            ui.centered(surface, fonts, "Dataset preview unavailable", image_rect.center, ui.C_MUTED, "small")

        ui_state["image_rect"] = image_rect

        source_btn = pygame.Rect(832, 188, 160, 28)
        ui.button(
            surface, source_btn,
            "HIDE SOURCE" if ui_state.get("show_source") else "SOURCE INFO",
            fonts, mouse_pos, small=True,
        )
        hint_btn = pygame.Rect(1004, 188, 160, 28)
        ui.button(surface, hint_btn, "HINT", fonts, mouse_pos, small=True)

        if ui_state.get("show_source") and item:
            ui.label(
                surface, fonts,
                ui.truncate(f"Product: {item.get('product_id') or 'n/a'}  ·  {item.get('dataset')}", 70),
                (452, 356), ui.C_MUTED, "small",
            )
            src = (item.get("source_portal") or item.get("source_url") or "")[:70]
            ui.label(surface, fonts, ui.truncate(f"Source: {src}", 70), (452, 374), ui.C_MUTED, "small")

        if needs and not avail:
            ui.label(
                surface, fonts,
                ui.truncate(item.get("reason") if item else "Dataset missing from local pack.", 80),
                (452, 400), ui.C_AMBER, "small",
            )
            ui.label(surface, fonts, "Task locked until verified local data is imported.", (452, 420), ui.C_AMBER, "small")
        else:
            ui.label(surface, fonts, ui.truncate(task["prompt"], 88), (452, 400), ui.C_TEXT, "small")
            kind = task.get("interaction", "choice")
            ox = 452
            if kind == "choice":
                for key, label in task.get("options") or []:
                    r = pygame.Rect(ox, 430, 230, 34)
                    sel = ui_state.get("selected_option") == key
                    pygame.draw.rect(surface, ui.C_SURFACE_2 if sel else ui.C_SURFACE, r, border_radius=6)
                    pygame.draw.rect(surface, ui.C_SIGNAL if sel else ui.C_EDGE, r, 1, border_radius=6)
                    ui.centered(surface, fonts, f"{key}) {ui.truncate(label, 20)}", r.center, ui.C_TEXT, "small")
                    option_rects[key] = r
                    ox += 240
            elif kind in ("route_compare", "timeline", "image_pick"):
                options = task.get("routes") or task.get("timeline_windows") or task.get("hotspots") or []
                for opt in options:
                    key = opt["id"]
                    label = opt.get("label") or key
                    r = pygame.Rect(ox, 430, 230, 34)
                    sel = ui_state.get("selected_option") == key
                    pygame.draw.rect(surface, ui.C_SURFACE_2 if sel else ui.C_SURFACE, r, border_radius=6)
                    pygame.draw.rect(surface, ui.C_SIGNAL if sel else ui.C_EDGE, r, 1, border_radius=6)
                    ui.centered(surface, fonts, ui.truncate(label, 24), r.center, ui.C_TEXT, "small")
                    option_rects[key] = r
                    hotspot_rects[key] = r
                    ox += 240
            elif kind == "marker":
                ui.label(surface, fonts, "Click the image to place a marker, then submit.", (452, 438), ui.C_MUTED, "small")

            if ui_state.get("hint_used"):
                ui.label(surface, fonts, ui.truncate(f"Hint: {task.get('hint', '')}", 70), (452, 472), ui.C_MUTED, "small")

            if done:
                ui.label(surface, fonts, "COMPLETED — RP already awarded.", (452, 508), ui.C_GREEN, "small")
                ui.label(surface, fonts, ui.truncate(task.get("explanation", ""), 80), (452, 532), ui.C_MUTED, "small")
            elif needs and not avail:
                pass
            else:
                submit = pygame.Rect(452, 508, 200, 40)
                ui.button(surface, submit, "SUBMIT", fonts, mouse_pos, accent=True, small=True)

        if ui_state.get("feedback"):
            ui.label(surface, fonts, ui.truncate(ui_state["feedback"], 80), (452, 560), ui.C_SIGNAL, "small")
        if ui_state.get("last_reward"):
            ui.label(surface, fonts, ui.truncate(ui_state["last_reward"], 70), (452, 580), ui.C_GREEN, "small")

    # Clearance footer for active mission
    if active:
        needed = camp.CLEARANCE_TASKS.get(active, [])
        done_n = sum(1 for t in needed if t in campaign["research_tasks_completed"])
        ui.label(
            surface, fonts,
            f"Clearance {camp.MISSION_META[active]['name']}: {done_n}/{len(needed)}",
            (72, 620),
            ui.C_SIGNAL if done_n == len(needed) else ui.C_MUTED,
            "small",
        )

    attr = ui.truncate(manifest.get("attribution", ""), 100)
    ui.label(surface, fonts, attr, (72, 648), ui.C_MUTED, "small")

    close = pygame.Rect(1000, 640, 200, 36)
    ui.button(surface, close, "CLOSE", fonts, mouse_pos, small=True)
    return {
        "tasks": task_rects,
        "options": option_rects,
        "hotspots": hotspot_rects,
        "submit": submit,
        "close": close,
        "source": source_btn,
        "hint": hint_btn,
        "image_rect": image_rect,
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
    hint = hit.get("hint")
    if hint and hint.width > 0 and hint.collidepoint(pos):
        ui_state["hint_used"] = True
        return False
    for tid, rect in hit.get("tasks", {}).items():
        if rect.collidepoint(pos):
            ui_state["selected_task"] = tid
            ui_state["selected_option"] = None
            ui_state["feedback"] = ""
            ui_state["last_reward"] = ""
            ui_state["show_source"] = False
            ui_state["hint_used"] = False
            ui_state["marker_pos"] = None
            return False

    # Image marker placement
    tid = ui_state.get("selected_task")
    task = rtasks.get_task(tid) if tid else None
    img_r = hit.get("image_rect")
    if task and task.get("interaction") == "marker" and img_r and img_r.width > 0 and img_r.collidepoint(pos):
        nx = (pos[0] - img_r.x) / max(1, img_r.w)
        ny = (pos[1] - img_r.y) / max(1, img_r.h)
        ui_state["marker_pos"] = (max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))
        return False

    for key, rect in hit.get("options", {}).items():
        if rect.collidepoint(pos):
            ui_state["selected_option"] = key
            return False

    if hit.get("submit") and hit["submit"].width > 0 and hit["submit"].collidepoint(pos):
        if not task:
            ui_state["feedback"] = "Select a task first."
            return False
        if tid in campaign["research_tasks_completed"]:
            ui_state["feedback"] = "Already completed."
            return False

        manifest = rdata.load_manifest()
        item = rdata.get_item(manifest, task["dataset_item"])
        if task.get("requires_dataset") and not rdata.item_available(item):
            ui_state["feedback"] = "Dataset unavailable — cannot award RP."
            return False
        # Soft check for browse imagery tasks that need a preview
        if task.get("interaction") in ("image_pick", "marker", "choice") and task["id"] not in (
            "res_1b_mola",
        ):
            if task.get("dataset_item") and not rdata.item_available(item) and task.get("requires_dataset", False):
                ui_state["feedback"] = "Browse dataset unavailable."
                return False

        kind = task.get("interaction", "choice")
        if kind == "marker":
            mp = ui_state.get("marker_pos")
            if not mp:
                ui_state["feedback"] = "Place a marker on the image first."
                return False
            correct, acc, first = rtasks.grade_marker(task, mp[0], mp[1])
        else:
            ans = ui_state.get("selected_option")
            if not ans:
                ui_state["feedback"] = "Choose an option before submitting."
                return False
            correct, acc, first = rtasks.grade(task, ans)

        if ui_state.get("hint_used"):
            acc = 0  # hint removes accuracy bonus if any

        if not correct:
            ui_state["feedback"] = "Not quite — review the evidence and try again."
            return False

        result = camp.award_research(campaign, tid, task["base_rp"], acc, first)
        ui_state["feedback"] = result["message"] + " · " + task.get("explanation", "")[:48]
        ui_state["last_reward"] = "Reward: " + ", ".join(result.get("breakdown", []))
        return False
    return False
