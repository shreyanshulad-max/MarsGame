"""Research Terminal — lesson-first optional research with Home / Base navigation.

Stages per activity:
  home → intro → visual → guide → practice → questions → result → home
"""

from __future__ import annotations

import pygame

from systems import campaign as camp
from systems import challenge_ui as ui
from systems import research_data as rdata
from systems import research_tasks as rtasks

STAGES = ("home", "intro", "visual", "guide", "practice", "questions", "result")


def make_ui_state() -> dict:
    return {
        "stage": "home",
        "selected_task": None,
        "selected_option": None,
        "feedback": "",
        "last_reward": "",
        "scroll": 0,
        "list_scroll": 0,
        "show_source": False,
        "hint_used": False,
        "marker_pos": None,
        "image_rect": None,
        "question_index": 0,
        "practice_done": False,
        "show_completed": False,
    }


def _nav_buttons(mouse_pos, fonts, surface, show_home: bool = True) -> dict:
    home = pygame.Rect(64, 36, 200, 32)
    base = pygame.Rect(980, 36, 220, 32)
    if show_home:
        ui.button(surface, home, "RESEARCH HOME", fonts, mouse_pos, small=True)
    else:
        home = pygame.Rect(0, 0, 0, 0)
    ui.button(surface, base, "RETURN TO BASE", fonts, mouse_pos, small=True)
    return {"home": home, "base": base}


def _blit_task_images(surface, task, manifest, rect: pygame.Rect, marker_pos=None):
    item = rdata.get_item(manifest, task.get("dataset_item"))
    img = rdata.load_image_surface(item) if item else None
    cmp_id = task.get("compare_item")
    img2 = rdata.load_image_surface(rdata.get_item(manifest, cmp_id)) if cmp_id else None
    pygame.draw.rect(surface, ui.C_SURFACE, rect, border_radius=8)
    if img and img2:
        half_w = rect.w // 2 - 6
        a = rdata.scale_to_fit(img, half_w, rect.h - 8)
        b = rdata.scale_to_fit(img2, half_w, rect.h - 8)
        if a:
            surface.blit(a, (rect.x + 4 + (half_w - a.get_width()) // 2, rect.y + 4 + (rect.h - 8 - a.get_height()) // 2))
        if b:
            surface.blit(b, (rect.centerx + 2 + (half_w - b.get_width()) // 2, rect.y + 4 + (rect.h - 8 - b.get_height()) // 2))
        pygame.draw.line(surface, ui.C_EDGE, (rect.centerx, rect.y + 4), (rect.centerx, rect.bottom - 4), 1)
    elif img:
        fitted = rdata.scale_to_fit(img, rect.w - 8, rect.h - 8)
        if fitted:
            surface.blit(
                fitted,
                (rect.x + (rect.w - fitted.get_width()) // 2, rect.y + (rect.h - fitted.get_height()) // 2),
            )
        if marker_pos:
            px = rect.x + int(marker_pos[0] * rect.w)
            py = rect.y + int(marker_pos[1] * rect.h)
            pygame.draw.circle(surface, ui.C_MARS, (px, py), 8, 2)
    else:
        missing = (item or {}).get("local_filename") or task.get("dataset_item") or "unknown"
        msg = f"Image unavailable: {missing}"
        font = pygame.font.SysFont("segoeui", 14)
        t = font.render(msg[:60], True, ui.C_AMBER)
        surface.blit(t, t.get_rect(center=rect.center))
        print(f"[research] missing image for {task.get('id')}: {missing}")
    pygame.draw.rect(surface, ui.C_EDGE, rect, 1, border_radius=8)
    return rect


def draw(surface, fonts, mouse_pos, campaign: dict, ui_state: dict) -> dict:
    ui.dim_backdrop(surface, 150)
    box = pygame.Rect(48, 24, 1184, 672)
    ui.panel(surface, box)
    stage = ui_state.get("stage", "home")
    tier = campaign.get("research_tier", 1)
    ui.header(
        surface, fonts, box,
        "RESEARCH TERMINAL",
        f"Optional · Tier {tier} · {campaign['research_points']} RP · Teach first, then questions",
    )

    hit = {
        "tasks": {},
        "options": {},
        "submit": pygame.Rect(0, 0, 0, 0),
        "next": pygame.Rect(0, 0, 0, 0),
        "source": pygame.Rect(0, 0, 0, 0),
        "hint": pygame.Rect(0, 0, 0, 0),
        "image_rect": None,
        "scroll_up": pygame.Rect(0, 0, 0, 0),
        "scroll_down": pygame.Rect(0, 0, 0, 0),
        "toggle_completed": pygame.Rect(0, 0, 0, 0),
        "close": pygame.Rect(0, 0, 0, 0),
    }
    nav = _nav_buttons(mouse_pos, fonts, surface, show_home=(stage != "home"))
    hit.update(nav)

    if stage == "home":
        return _draw_home(surface, fonts, mouse_pos, campaign, ui_state, hit)
    task = rtasks.get_task(ui_state.get("selected_task"))
    if not task:
        ui_state["stage"] = "home"
        return _draw_home(surface, fonts, mouse_pos, campaign, ui_state, hit)

    if stage == "intro":
        return _draw_intro(surface, fonts, mouse_pos, campaign, ui_state, hit, task)
    if stage == "visual":
        return _draw_visual(surface, fonts, mouse_pos, campaign, ui_state, hit, task)
    if stage == "guide":
        return _draw_guide(surface, fonts, mouse_pos, campaign, ui_state, hit, task)
    if stage == "practice":
        return _draw_practice(surface, fonts, mouse_pos, campaign, ui_state, hit, task)
    if stage == "questions":
        return _draw_questions(surface, fonts, mouse_pos, campaign, ui_state, hit, task)
    if stage == "result":
        return _draw_result(surface, fonts, mouse_pos, campaign, ui_state, hit, task)
    ui_state["stage"] = "home"
    return _draw_home(surface, fonts, mouse_pos, campaign, ui_state, hit)


def _draw_home(surface, fonts, mouse_pos, campaign, ui_state, hit):
    available = rtasks.available_tasks(campaign)
    completed = rtasks.completed_tasks(campaign)
    ui.label(surface, fonts, "AVAILABLE RESEARCH (optional)", (72, 100), ui.C_MUTED, "small")
    ui.label(
        surface, fonts,
        f"Completed {len(completed)}  ·  Available {len(available)}  ·  RP {campaign['research_points']}",
        (72, 124),
        ui.C_SIGNAL,
        "small",
    )
    ui.label(
        surface, fonts,
        "Research earns RP for purchases. Missions unlock only by completing the previous mission.",
        (72, 148),
        ui.C_MUTED,
        "small",
    )

    list_box = pygame.Rect(72, 180, 700, 420)
    pygame.draw.rect(surface, ui.C_BG, list_box, border_radius=8)
    pygame.draw.rect(surface, ui.C_EDGE, list_box, 1, border_radius=8)

    scroll = int(ui_state.get("list_scroll", 0))
    row_h = 56
    visible = max(1, list_box.h // row_h)
    max_scroll = max(0, len(available) - visible)
    scroll = max(0, min(scroll, max_scroll))
    ui_state["list_scroll"] = scroll

    y = list_box.y + 12
    for t in available[scroll : scroll + visible]:
        r = pygame.Rect(list_box.x + 12, y, list_box.w - 24, 48)
        sel = ui_state.get("selected_task") == t["id"]
        pygame.draw.rect(surface, ui.C_SURFACE_2 if sel else ui.C_SURFACE, r, border_radius=6)
        pygame.draw.rect(surface, ui.C_SIGNAL if sel else ui.C_EDGE, r, 1, border_radius=6)
        ui.label(surface, fonts, f"T{t['tier']}  {ui.truncate(t['title'], 40)}", (r.x + 12, r.y + 8), ui.C_TEXT, "small")
        ui.label(surface, fonts, f"+{t['base_rp']} RP", (r.x + 12, r.y + 28), ui.C_MUTED, "small")
        hit["tasks"][t["id"]] = r
        y += row_h

    if not available:
        ui.centered(surface, fonts, "No pending research in this tier.", (list_box.centerx, list_box.centery), ui.C_MUTED, "body")

    # Scroll controls when needed
    if max_scroll > 0:
        hit["scroll_up"] = pygame.Rect(790, 180, 40, 36)
        hit["scroll_down"] = pygame.Rect(790, 564, 40, 36)
        ui.button(surface, hit["scroll_up"], "▲", fonts, mouse_pos, small=True)
        ui.button(surface, hit["scroll_down"], "▼", fonts, mouse_pos, small=True)

    # Completed history (collapsed list)
    hit["toggle_completed"] = pygame.Rect(850, 180, 340, 36)
    label = "HIDE COMPLETED" if ui_state.get("show_completed") else f"COMPLETED RESEARCH ({len(completed)})"
    ui.button(surface, hit["toggle_completed"], label, fonts, mouse_pos, small=True)
    if ui_state.get("show_completed"):
        cy = 230
        for t in completed[:8]:
            ui.label(surface, fonts, f"✓  {ui.truncate(t['title'], 34)}", (860, cy), ui.C_GREEN, "small")
            cy += 28
        if len(completed) > 8:
            ui.label(surface, fonts, f"…and {len(completed) - 8} more", (860, cy), ui.C_MUTED, "small")

    open_btn = pygame.Rect(850, 520, 340, 44)
    can_open = bool(ui_state.get("selected_task") and ui_state["selected_task"] in {t["id"] for t in available})
    ui.button(surface, open_btn, "START LESSON", fonts, mouse_pos, accent=can_open)
    hit["next"] = open_btn if can_open else pygame.Rect(0, 0, 0, 0)
    hit["close"] = hit["base"]
    return hit


def _draw_intro(surface, fonts, mouse_pos, campaign, ui_state, hit, task):
    lesson = rtasks.lesson_text(task)
    ui.label(surface, fonts, task["title"], (72, 100), ui.C_TEXT, "body")
    ui.label(surface, fonts, f"Optional reward  {task['base_rp']} RP  ·  Tier {task['tier']}", (72, 132), ui.C_SIGNAL, "small")
    lines = [
        ("Why it matters", lesson["why"]),
        ("What you will learn", lesson["learn"]),
        ("Dataset", f"{task.get('dataset_item', 'n/a')}  ·  NASA educational local pack"),
    ]
    y = 180
    for title, body in lines:
        ui.label(surface, fonts, title, (72, y), ui.C_MUTED, "small")
        ui.label(surface, fonts, ui.truncate(body, 100), (72, y + 26), ui.C_TEXT, "body")
        y += 80
    hit["next"] = pygame.Rect(480, 600, 280, 44)
    ui.button(surface, hit["next"], "CONTINUE TO IMAGES", fonts, mouse_pos, accent=True)
    hit["close"] = hit["base"]
    return hit


def _draw_visual(surface, fonts, mouse_pos, campaign, ui_state, hit, task):
    manifest = rdata.load_manifest()
    item = rdata.get_item(manifest, task.get("dataset_item"))
    ui.label(surface, fonts, "VISUAL LEARNING", (72, 100), ui.C_MUTED, "small")
    ui.label(surface, fonts, ui.truncate(task.get("intro", ""), 95), (72, 126), ui.C_TEXT, "small")
    img_rect = pygame.Rect(72, 160, 900, 360)
    _blit_task_images(surface, task, manifest, img_rect)
    hit["image_rect"] = img_rect
    if item:
        ui.label(
            surface, fonts,
            ui.truncate(
                f"Product {(item.get('product_id') or 'n/a')}  ·  {item.get('mission_or_instrument', '')}",
                90,
            ),
            (72, 536),
            ui.C_MUTED,
            "small",
        )
        ui.label(
            surface, fonts,
            ui.truncate(f"Source: {item.get('source_portal') or item.get('source_url') or ''}", 90),
            (72, 560),
            ui.C_MUTED,
            "small",
        )
    hit["next"] = pygame.Rect(480, 600, 280, 44)
    ui.button(surface, hit["next"], "CONTINUE", fonts, mouse_pos, accent=True)
    hit["close"] = hit["base"]
    return hit


def _draw_guide(surface, fonts, mouse_pos, campaign, ui_state, hit, task):
    lesson = rtasks.lesson_text(task)
    ui.label(surface, fonts, "GUIDED EXPLANATION", (72, 100), ui.C_MUTED, "small")
    ui.label(surface, fonts, ui.truncate(lesson["guide"], 100), (72, 140), ui.C_TEXT, "body")
    bullets = [
        "Look at the image labels and compare features.",
        "Use the hint if you get stuck — it only reduces optional bonuses.",
        "Questions come after practice and test what this lesson taught.",
    ]
    y = 220
    for b in bullets:
        ui.label(surface, fonts, f"• {b}", (90, y), ui.C_TEXT, "small")
        y += 36
    hit["next"] = pygame.Rect(480, 600, 280, 44)
    ui.button(surface, hit["next"], "START PRACTICE", fonts, mouse_pos, accent=True)
    hit["close"] = hit["base"]
    return hit


def _draw_practice(surface, fonts, mouse_pos, campaign, ui_state, hit, task):
    manifest = rdata.load_manifest()
    lesson = rtasks.lesson_text(task)
    ui.label(surface, fonts, "GUIDED PRACTICE (no RP yet)", (72, 100), ui.C_MUTED, "small")
    ui.label(surface, fonts, ui.truncate(lesson["practice_prompt"], 95), (72, 126), ui.C_TEXT, "small")
    img_rect = pygame.Rect(72, 160, 620, 300)
    _blit_task_images(surface, task, manifest, img_rect, ui_state.get("marker_pos"))
    hit["image_rect"] = img_rect

    # Practice uses same options as first question / interaction
    qs = rtasks.questions_for(task)
    q0 = qs[0] if qs else {}
    kind = q0.get("kind") or task.get("interaction", "choice")
    ox, oy = 720, 180
    if kind == "marker":
        ui.label(surface, fonts, "Click the image to place a marker.", (720, 180), ui.C_TEXT, "small")
    else:
        opts = q0.get("options") or task.get("options") or []
        if not opts:
            rows = task.get("routes") or task.get("timeline_windows") or task.get("hotspots") or []
            opts = [(r["id"], r.get("label") or r["id"]) for r in rows]
        for key, label in opts:
            r = pygame.Rect(ox, oy, 420, 40)
            sel = ui_state.get("selected_option") == key
            pygame.draw.rect(surface, ui.C_SURFACE_2 if sel else ui.C_SURFACE, r, border_radius=6)
            pygame.draw.rect(surface, ui.C_SIGNAL if sel else ui.C_EDGE, r, 1, border_radius=6)
            ui.label(surface, fonts, ui.truncate(f"{key}) {label}", 42), (r.x + 12, r.y + 10), ui.C_TEXT, "small")
            hit["options"][key] = r
            oy += 52

    if ui_state.get("practice_done"):
        ui.label(surface, fonts, "Practice complete — continue to questions.", (72, 480), ui.C_GREEN, "small")
        hit["next"] = pygame.Rect(480, 600, 280, 44)
        ui.button(surface, hit["next"], "CONTINUE TO QUESTIONS", fonts, mouse_pos, accent=True)
    else:
        hit["submit"] = pygame.Rect(720, 480, 200, 40)
        ui.button(surface, hit["submit"], "CHECK PRACTICE", fonts, mouse_pos, accent=True, small=True)
        if ui_state.get("feedback"):
            ui.label(surface, fonts, ui.truncate(ui_state["feedback"], 50), (720, 530), ui.C_AMBER, "small")
    hit["close"] = hit["base"]
    return hit


def _draw_questions(surface, fonts, mouse_pos, campaign, ui_state, hit, task):
    manifest = rdata.load_manifest()
    qs = rtasks.questions_for(task)
    idx = int(ui_state.get("question_index", 0))
    idx = max(0, min(idx, len(qs) - 1)) if qs else 0
    ui_state["question_index"] = idx
    q = qs[idx] if qs else {"prompt": "No questions configured.", "options": [], "kind": "choice"}

    ui.label(surface, fonts, f"Question {idx + 1} of {len(qs)}", (72, 100), ui.C_SIGNAL, "small")
    ui.label(surface, fonts, ui.truncate(q.get("prompt", ""), 95), (72, 126), ui.C_TEXT, "body")

    img_rect = pygame.Rect(72, 168, 560, 260)
    _blit_task_images(surface, task, manifest, img_rect, ui_state.get("marker_pos"))
    hit["image_rect"] = img_rect

    kind = q.get("kind") or task.get("interaction", "choice")
    ox, oy = 660, 168
    if kind == "marker":
        ui.label(surface, fonts, "Click the image, then submit.", (660, 180), ui.C_TEXT, "small")
    else:
        opts = q.get("options") or []
        if not opts:
            rows = task.get("routes") or task.get("timeline_windows") or task.get("hotspots") or []
            opts = [(r["id"], r.get("label") or r["id"]) for r in rows]
        # Vertical list so the last option is never clipped horizontally
        for key, label in opts:
            r = pygame.Rect(ox, oy, 480, 44)
            # Keep within panel
            if r.bottom > 560:
                break
            sel = ui_state.get("selected_option") == key
            pygame.draw.rect(surface, ui.C_SURFACE_2 if sel else ui.C_SURFACE, r, border_radius=6)
            pygame.draw.rect(surface, ui.C_SIGNAL if sel else ui.C_EDGE, r, 1, border_radius=6)
            ui.label(surface, fonts, ui.truncate(f"{key}) {label}", 48), (r.x + 12, r.y + 12), ui.C_TEXT, "small")
            hit["options"][key] = r
            oy += 56

    hit["hint"] = pygame.Rect(660, 520, 120, 32)
    ui.button(surface, hit["hint"], "HINT", fonts, mouse_pos, small=True)
    if ui_state.get("hint_used"):
        ui.label(surface, fonts, ui.truncate(q.get("hint") or task.get("hint", ""), 55), (790, 526), ui.C_MUTED, "small")

    hit["submit"] = pygame.Rect(480, 600, 280, 44)
    ui.button(surface, hit["submit"], "SUBMIT ANSWER", fonts, mouse_pos, accent=True)
    if ui_state.get("feedback"):
        ui.label(surface, fonts, ui.truncate(ui_state["feedback"], 80), (72, 560), ui.C_AMBER, "small")
    hit["close"] = hit["base"]
    return hit


def _draw_result(surface, fonts, mouse_pos, campaign, ui_state, hit, task):
    ui.label(surface, fonts, "RESULT", (72, 120), ui.C_MUTED, "small")
    ui.label(surface, fonts, ui.truncate(ui_state.get("feedback") or "Completed.", 90), (72, 160), ui.C_GREEN, "body")
    ui.label(surface, fonts, ui.truncate(ui_state.get("last_reward") or "", 90), (72, 210), ui.C_SIGNAL, "body")
    ui.label(surface, fonts, ui.truncate(task.get("explanation", ""), 95), (72, 270), ui.C_TEXT, "small")
    ui.label(
        surface, fonts,
        "This activity is marked completed and will not appear in Available Research.",
        (72, 340),
        ui.C_MUTED,
        "small",
    )
    hit["next"] = pygame.Rect(420, 600, 400, 44)
    ui.button(surface, hit["next"], "BACK TO RESEARCH HOME", fonts, mouse_pos, accent=True)
    hit["close"] = hit["base"]
    return hit


def handle_event(campaign, inventory, event, ui_state, hit) -> bool:
    """Handle click. Returns True if should close Research Terminal (Return to Base)."""
    if event.type == pygame.MOUSEWHEEL:
        if ui_state.get("stage") == "home":
            ui_state["list_scroll"] = max(0, int(ui_state.get("list_scroll", 0)) - int(event.y))
        return False
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return False
    pos = event.pos

    # Global navigation
    if hit.get("base") and hit["base"].width > 0 and hit["base"].collidepoint(pos):
        return True
    if hit.get("home") and hit["home"].width > 0 and hit["home"].collidepoint(pos):
        ui_state["stage"] = "home"
        ui_state["feedback"] = ""
        ui_state["selected_option"] = None
        ui_state["question_index"] = 0
        ui_state["practice_done"] = False
        ui_state["marker_pos"] = None
        return False

    stage = ui_state.get("stage", "home")

    if stage == "home":
        if hit.get("scroll_up") and hit["scroll_up"].width and hit["scroll_up"].collidepoint(pos):
            ui_state["list_scroll"] = max(0, int(ui_state.get("list_scroll", 0)) - 1)
            return False
        if hit.get("scroll_down") and hit["scroll_down"].width and hit["scroll_down"].collidepoint(pos):
            ui_state["list_scroll"] = int(ui_state.get("list_scroll", 0)) + 1
            return False
        if hit.get("toggle_completed") and hit["toggle_completed"].collidepoint(pos):
            ui_state["show_completed"] = not ui_state.get("show_completed", False)
            return False
        for tid, rect in hit.get("tasks", {}).items():
            if rect.collidepoint(pos):
                ui_state["selected_task"] = tid
                return False
        if hit.get("next") and hit["next"].width > 0 and hit["next"].collidepoint(pos):
            if ui_state.get("selected_task"):
                ui_state["stage"] = "intro"
                ui_state["feedback"] = ""
                ui_state["last_reward"] = ""
                ui_state["selected_option"] = None
                ui_state["question_index"] = 0
                ui_state["practice_done"] = False
                ui_state["hint_used"] = False
                ui_state["marker_pos"] = None
            return False
        return False

    task = rtasks.get_task(ui_state.get("selected_task"))
    if not task:
        ui_state["stage"] = "home"
        return False

    # Shared option / marker clicks
    img_r = hit.get("image_rect")
    if task and img_r and img_r.width > 0 and img_r.collidepoint(pos) and stage in ("practice", "questions"):
        qs = rtasks.questions_for(task)
        qidx = int(ui_state.get("question_index", 0))
        qkind = qs[qidx].get("kind") if qs and 0 <= qidx < len(qs) else None
        if task.get("interaction") == "marker" or qkind == "marker":
            nx = (pos[0] - img_r.x) / max(1, img_r.w)
            ny = (pos[1] - img_r.y) / max(1, img_r.h)
            ui_state["marker_pos"] = (max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))
            return False

    for key, rect in hit.get("options", {}).items():
        if rect.collidepoint(pos):
            ui_state["selected_option"] = key
            return False

    if hit.get("hint") and hit["hint"].width > 0 and hit["hint"].collidepoint(pos):
        ui_state["hint_used"] = True
        return False

    if stage in ("intro", "visual", "guide") and hit.get("next") and hit["next"].width and hit["next"].collidepoint(pos):
        nxt = {"intro": "visual", "visual": "guide", "guide": "practice"}[stage]
        ui_state["stage"] = nxt
        ui_state["feedback"] = ""
        return False

    if stage == "practice":
        if hit.get("submit") and hit["submit"].width and hit["submit"].collidepoint(pos):
            ok = _check_practice(task, ui_state)
            if ok:
                ui_state["practice_done"] = True
                ui_state["feedback"] = "Good practice — continue when ready."
            else:
                ui_state["feedback"] = "Not yet — review the lesson and try again."
            return False
        if ui_state.get("practice_done") and hit.get("next") and hit["next"].width and hit["next"].collidepoint(pos):
            ui_state["stage"] = "questions"
            ui_state["question_index"] = 0
            ui_state["selected_option"] = None
            ui_state["feedback"] = ""
            ui_state["marker_pos"] = None
            return False
        return False

    if stage == "questions":
        if hit.get("submit") and hit["submit"].width and hit["submit"].collidepoint(pos):
            _submit_question(campaign, task, ui_state)
            return False
        return False

    if stage == "result" and hit.get("next") and hit["next"].width and hit["next"].collidepoint(pos):
        ui_state["stage"] = "home"
        ui_state["selected_task"] = None
        ui_state["feedback"] = ""
        ui_state["last_reward"] = ""
        return False

    return False


def _check_practice(task, ui_state) -> bool:
    qs = rtasks.questions_for(task)
    q = qs[0] if qs else {}
    kind = q.get("kind") or task.get("interaction", "choice")
    if kind == "marker":
        mp = ui_state.get("marker_pos")
        if not mp:
            return False
        ok, _, _ = rtasks.grade_marker(task, mp[0], mp[1])
        return ok
    ans = ui_state.get("selected_option")
    if not ans:
        return False
    ok, _, _ = rtasks.grade(task, ans, q)
    return ok


def _submit_question(campaign, task, ui_state) -> None:
    if task["id"] in campaign.get("research_tasks_completed", []):
        ui_state["feedback"] = "Already completed — no additional RP."
        ui_state["stage"] = "result"
        return
    qs = rtasks.questions_for(task)
    idx = int(ui_state.get("question_index", 0))
    q = qs[idx]
    kind = q.get("kind") or task.get("interaction", "choice")
    if kind == "marker":
        mp = ui_state.get("marker_pos")
        if not mp:
            ui_state["feedback"] = "Place a marker on the image first."
            return
        correct, acc, first = rtasks.grade_marker(task, mp[0], mp[1])
    else:
        ans = ui_state.get("selected_option")
        if not ans:
            ui_state["feedback"] = "Choose an option before submitting."
            return
        correct, acc, first = rtasks.grade(task, ans, q)
    if ui_state.get("hint_used"):
        acc = 0
    if not correct:
        ui_state["feedback"] = "Not quite — review the lesson and try again."
        return

    # Advance through multi-question activities before awarding
    if idx + 1 < len(qs):
        ui_state["question_index"] = idx + 1
        ui_state["selected_option"] = None
        ui_state["marker_pos"] = None
        ui_state["feedback"] = f"Correct! Continue to question {idx + 2} of {len(qs)}."
        return

    result = camp.award_research(campaign, task["id"], task["base_rp"], acc, first)
    ui_state["feedback"] = result["message"] + " · " + (q.get("explanation") or task.get("explanation", ""))[:60]
    ui_state["last_reward"] = "Reward: " + ", ".join(result.get("breakdown", []))
    ui_state["stage"] = "result"
