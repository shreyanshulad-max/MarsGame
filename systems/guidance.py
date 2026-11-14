"""Dynamic campaign guiding arrow + objective resolution."""

from __future__ import annotations

import math

import pygame

from systems import campaign as camp
from systems import challenge_ui as ui
from systems import materials as mats
from systems import procurement as proc
from systems import research_tasks as rtasks

# Zone search centroids for undiscovered essential materials
ZONE_SEARCH = {
    "Communication Area": (420, 820),
    "Communication / Equipment Storage": (420, 820),
    "Damaged Equipment Storage": (1700, 1150),
    "Solar Farm": (2600, 960),
    "Rover Maintenance Area": (620, 1740),
    "Research Area": (2480, 480),
}


def make_guidance() -> dict:
    return {
        "enabled": True,
        "display_angle": 0.0,  # smoothed degrees
        "pulse": 0.0,
        "objective": None,  # resolved dict
        "waypoint_x": 0.0,
        "waypoint_y": 0.0,
        "route_hint": False,  # True if waypoint is detour (not final dest)
    }


def _station_pos(colony: dict, station_id: str) -> tuple[float, float] | None:
    for st in colony.get("stations", []):
        if st["id"] == station_id:
            return float(st["pos"][0]), float(st["pos"][1])
    return None


def _kit_missing(inventory: dict, kit: list[str]) -> list[str]:
    missing = []
    for mid in kit:
        if inventory["stock"].get(mid, {}).get("qty", 0) < 1:
            missing.append(mid)
    return missing


def _kit_cost(missing: list[str]) -> int:
    return sum(proc.price_of(mid) for mid in missing)


def _incomplete_tier_tasks(campaign: dict) -> list[dict]:
    tier = campaign.get("research_tier", 1)
    done = set(campaign.get("research_tasks_completed", []))
    # Prefer core clearance tasks for the active mission
    active = camp.active_mission_id(campaign)
    if active:
        core = []
        for tid in camp.CLEARANCE_TASKS.get(active, []):
            t = rtasks.get_task(tid)
            if t and tid not in done and t["tier"] <= tier:
                core.append(t)
        if core:
            return core
    return [t for t in rtasks.tasks_for_mission_tier(tier) if t["id"] not in done]


def _find_cache_for_material(colony: dict, discovery: dict, mid: str) -> dict | None:
    """Return collectible for material if present; prefer discovered over hidden."""
    unknown = None
    for it in colony.get("collectibles", []):
        if it.get("collected"):
            continue
        if it.get("material") != mid:
            continue
        uid = it["id"]
        known = uid in discovery.get("identified", set()) or uid in discovery.get("scanned_ids", set())
        if known:
            return {"item": it, "known": True}
        if unknown is None:
            unknown = {"item": it, "known": False}
    return unknown


def _search_area_for(mid: str) -> tuple[float, float, str]:
    loc = mats.CATALOG.get(mid, {}).get("location", "Outer Mars Terrain")
    pos = ZONE_SEARCH.get(loc)
    if pos:
        return pos[0], pos[1], loc
    return 1600.0, 1100.0, "Search the colony zones"


def resolve_objective(
    campaign: dict,
    inventory: dict,
    colony: dict,
    discovery: dict,
    current_screen: str = "base",
    challenge_hint: str = "",
) -> dict:
    """
    Returns objective dict:
      kind, title, task, dest_name, x, y, exact (bool), icon
    """
    # In-progress challenge: guide to current challenge objective text (stay at station)
    mid_active = None
    for mid in camp.MISSION_ORDER:
        if camp.mission_status(campaign, mid) == camp.STATUS_IN_PROGRESS:
            mid_active = mid
            break

    if mid_active and current_screen not in ("base", "title", "briefing", "dashboard", "research", "shop"):
        meta = camp.MISSION_META[mid_active]
        pos = _station_pos(colony, meta["station"]) or (1600, 1200)
        return {
            "kind": "challenge",
            "title": meta["name"],
            "task": challenge_hint or "Continue the active challenge objectives.",
            "dest_name": meta["name"] + " station",
            "x": pos[0],
            "y": pos[1],
            "exact": True,
            "icon": "mission",
        }

    if campaign.get("campaign_completed"):
        # Final report — guide to research lab / habitat as report hub
        pos = _station_pos(colony, "research") or (2350, 500)
        return {
            "kind": "final",
            "title": "Final Mission Report",
            "task": "Open Campaign (C) → Final Report to review the campaign.",
            "dest_name": "Research Terminal",
            "x": pos[0],
            "y": pos[1],
            "exact": True,
            "icon": "final",
        }

    # Next unlocked incomplete mission
    next_mission = None
    for mid in camp.MISSION_ORDER:
        st = camp.mission_status(campaign, mid)
        if st in (camp.STATUS_AVAILABLE, camp.STATUS_IN_PROGRESS):
            next_mission = mid
            break

    if next_mission is None:
        pos = _station_pos(colony, "research") or (2350, 500)
        return {
            "kind": "idle",
            "title": "Explore Mars",
            "task": "All primary missions complete.",
            "dest_name": "Research Zone",
            "x": pos[0],
            "y": pos[1],
            "exact": True,
            "icon": "explore",
        }

    meta = camp.MISSION_META[next_mission]
    missing = _kit_missing(inventory, meta["kit"])
    cost = _kit_cost(missing)
    rp = campaign.get("research_points", 0)
    research_pos = _station_pos(colony, "research") or (2350, 500)
    shop_pos = _station_pos(colony, "shop") or (1520, 1120)
    mission_pos = _station_pos(colony, meta["station"]) or (1600, 1200)
    incomplete = _incomplete_tier_tasks(campaign)

    # Prefer a discovered free cache for any missing kit item (exact marker only)
    if missing:
        for mid in missing:
            found = _find_cache_for_material(colony, discovery, mid)
            if found and found["known"]:
                it = found["item"]
                return {
                    "kind": "supply",
                    "title": f"Collect {mats.CATALOG[mid]['name']}",
                    "task": "Pick up the discovered supply cache.",
                    "dest_name": it.get("name", mats.CATALOG[mid]["name"]),
                    "x": float(it["pos"][0]),
                    "y": float(it["pos"][1]),
                    "exact": True,
                    "icon": "supply",
                }

    # Prefer collecting/searching world supplies; research is optional RP source
    if missing and rp >= cost and cost > 0:
        return {
            "kind": "shop",
            "title": "Buy Mission Kit",
            "task": f"Optional: purchase missing parts for {meta['name']} ({cost} RP).",
            "dest_name": "Procurement Station",
            "x": shop_pos[0],
            "y": shop_pos[1],
            "exact": True,
            "icon": "shop",
        }

    if missing and incomplete and rp < cost:
        return {
            "kind": "research",
            "title": "Optional Research",
            "task": f"Earn RP for purchases, or search the colony for {mats.CATALOG[missing[0]]['name']}.",
            "dest_name": "Research Terminal",
            "x": research_pos[0],
            "y": research_pos[1],
            "exact": True,
            "icon": "research",
        }

    # Undiscovered mandatory cache — search region only (never exact coords)
    if missing:
        mid = missing[0]
        found = _find_cache_for_material(colony, discovery, mid)
        if found and not found["known"]:
            sx, sy, region = _search_area_for(mid)
            return {
                "kind": "search",
                "title": f"Search for {mats.CATALOG[mid]['name']}",
                "task": f"Scan and explore near {region}. Exact cache hidden until discovered.",
                "dest_name": f"Search: {region}",
                "x": sx,
                "y": sy,
                "exact": False,
                "icon": "search",
            }

    # 4 / 5 / 6: materials ready → unlocked mission station (never locked)
    return {
        "kind": "mission",
        "title": meta["name"],
        "task": f"Enter the station — {meta['short']}",
        "dest_name": meta["name"] + " Station",
        "x": mission_pos[0],
        "y": mission_pos[1],
        "exact": True,
        "icon": "mission",
    }


def _segment_hits_collider(x0, y0, x1, y1, colliders, pad: int = 10) -> pygame.Rect | None:
    """Return first collider whose inflated rect intersects the segment AABB tightly."""
    steps = max(4, int(math.hypot(x1 - x0, y1 - y0) / 24))
    for i in range(1, steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        pt = pygame.Rect(int(x) - 4, int(y) - 4, 8, 8)
        for col in colliders:
            if col.inflate(pad, pad).colliderect(pt):
                return col
    return None


def _detour_around(astro, dest_x, dest_y, blocker: pygame.Rect) -> tuple[float, float]:
    """Pick a corner of the blocker that clears the path toward dest."""
    inflated = blocker.inflate(40, 40)
    corners = [
        (inflated.left, inflated.top),
        (inflated.right, inflated.top),
        (inflated.left, inflated.bottom),
        (inflated.right, inflated.bottom),
    ]
    # Prefer corner closest to both player and destination
    best = None
    best_score = 1e18
    for cx, cy in corners:
        score = math.hypot(cx - astro["x"], cy - astro["y"]) + math.hypot(cx - dest_x, cy - dest_y)
        if score < best_score:
            best_score = score
            best = (float(cx), float(cy))
    return best or (dest_x, dest_y)


def compute_waypoint(astro: dict, objective: dict, colliders: list) -> tuple[float, float, bool]:
    """
    Obstacle-aware next waypoint. Returns (wx, wy, is_detour).
    If blocked by a building, steer around it; else point at destination.
    """
    dx, dy = objective["x"], objective["y"]
    hit = _segment_hits_collider(astro["x"], astro["y"], dx, dy, colliders)
    if hit is None:
        return dx, dy, False
    wx, wy = _detour_around(astro, dx, dy, hit)
    return wx, wy, True


def update(
    guidance: dict,
    dt: float,
    astro: dict,
    objective: dict | None,
    colliders: list | None = None,
) -> None:
    guidance["pulse"] += dt
    guidance["objective"] = objective
    if not objective:
        return
    cols = colliders or []
    wx, wy, detour = compute_waypoint(astro, objective, cols)
    guidance["waypoint_x"] = wx
    guidance["waypoint_y"] = wy
    guidance["route_hint"] = detour
    dx = wx - astro["x"]
    dy = wy - astro["y"]
    target = math.degrees(math.atan2(dy, dx))
    # Smooth shortest-angle lerp
    cur = guidance["display_angle"]
    diff = (target - cur + 180) % 360 - 180
    guidance["display_angle"] = (cur + diff * min(1.0, 8.0 * dt)) % 360


def _world_to_screen(cam: dict, wx: float, wy: float) -> tuple[int, int]:
    return int(wx - cam["x"] - cam.get("ox", 0)), int(wy - cam["y"] - cam.get("oy", 0))


def draw_world_arrow(surface, fonts, guidance: dict, astro: dict, cam: dict) -> None:
    """
    One guidance indicator:
      - Off-screen → edge arrow + dest + distance
      - On-screen  → subtle diamond at destination (no floating HUD above player)
    Objective text lives in the explore HUD card only.
    """
    if not guidance.get("enabled"):
        return
    obj = guidance.get("objective")
    if not obj:
        return

    col = ui.C_SIGNAL if obj.get("exact") else ui.C_AMBER
    dist = math.hypot(obj["x"] - astro["x"], obj["y"] - astro["y"])
    dest_x = guidance.get("waypoint_x", obj["x"])
    dest_y = guidance.get("waypoint_y", obj["y"])
    tx, ty = _world_to_screen(cam, dest_x, dest_y)
    # Prefer final objective marker when close / exact on screen
    fx, fy = _world_to_screen(cam, obj["x"], obj["y"])
    vw, vh = cam["view_w"], cam["view_h"]
    margin = 40
    on_screen = (24 <= fx <= vw - 24) and (24 <= fy <= vh - 24)

    pulse = 0.9 + 0.1 * abs(math.sin(guidance["pulse"] * 2.4))

    if on_screen:
        # Subtle world marker at destination only
        r = 10 if obj.get("exact") else 16
        pygame.draw.circle(surface, col, (fx, fy), int(r * pulse), 1)
        pygame.draw.polygon(
            surface, col,
            [(fx, fy - 7), (fx + 5, fy), (fx, fy + 7), (fx - 5, fy)],
        )
        if dist < 100 and obj.get("exact"):
            near = fonts["small"].render("E", True, ui.C_GREEN)
            surface.blit(near, near.get_rect(center=(fx, fy - 18)))
        return

    # Screen-edge indicator (single directional cue)
    # Keep clear of status chips (top-right) and minimap (bottom-right)
    cx0, cy0 = vw // 2, vh // 2
    dx, dy = dest_x - (cam["x"] + vw * 0.5), dest_y - (cam["y"] + vh * 0.55)
    if abs(dx) < 1 and abs(dy) < 1:
        dx = 1.0
    scale_x = ((vw / 2 - margin) / abs(dx)) if dx else 1e9
    scale_y = ((vh / 2 - margin) / abs(dy)) if dy else 1e9
    scale = min(scale_x, scale_y)
    ex = int(cx0 + dx * scale)
    ey = int(cy0 + dy * scale)
    ex = max(margin, min(vw - margin - 180, ex))  # leave room for chips/minimap
    ey = max(margin + 8, min(vh - margin - 40, ey))
    pygame.draw.polygon(
        surface, col,
        [(ex, ey - 14), (ex + 10, ey), (ex, ey + 14), (ex - 10, ey)],
        1,
    )
    ta = math.radians(guidance["display_angle"])
    pygame.draw.polygon(
        surface,
        col,
        [
            (ex + math.cos(ta) * 11, ey + math.sin(ta) * 11),
            (ex + math.cos(ta + 2.4) * 6, ey + math.sin(ta + 2.4) * 6),
            (ex + math.cos(ta - 2.4) * 6, ey + math.sin(ta - 2.4) * 6),
        ],
    )
    edge_lbl = fonts["small"].render(f"{obj['dest_name'][:14]}  {int(dist)}m", True, ui.C_TEXT)
    # Keep label inside screen
    lr = edge_lbl.get_rect(center=(ex, ey - 22))
    lr.clamp_ip(pygame.Rect(8, 8, vw - 16, vh - 16))
    surface.blit(edge_lbl, lr)


def draw_hud_panel(surface, fonts, guidance: dict) -> None:
    """Deprecated — objective lives in explore HUD. Kept as no-op for callers."""
    return


def objective_label(obj: dict | None, fallback: str = "") -> str:
    if not obj:
        return fallback
    prefix = {
        "research": "RESEARCH",
        "shop": "PROCURE",
        "mission": "MISSION",
        "challenge": "ACTIVE",
        "supply": "SUPPLY",
        "search": "SEARCH",
        "final": "REPORT",
        "idle": "EXPLORE",
    }.get(obj.get("kind", ""), "NAV")
    return f"{prefix}: {obj['title']} — {obj['task']}"
