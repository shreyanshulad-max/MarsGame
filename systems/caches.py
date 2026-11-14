"""Mission-specific seeded supply caches — reproducible, never blocks essential kits."""

from __future__ import annotations

import random

from systems import interactions
from systems import materials as mats

# Candidate locations away from buildings / spawn (deterministic pick via seed)
CANDIDATE_SITES = [
    (900, 600), (1100, 400), (1800, 700), (2000, 1400), (1400, 1600),
    (600, 1100), (2400, 1200), (2800, 600), (300, 1400), (2100, 1800),
    (1000, 1800), (1600, 500), (2600, 1600), (700, 400), (1900, 1000),
    (1250, 750), (2050, 550), (850, 1500), (2350, 900), (1500, 1300),
]


def _stable_str_hash(text: str) -> int:
    """Process-independent string hash for reproducible seeds."""
    h = 2166136261
    for ch in text:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _mission_rng(seed: int, mission_id: str) -> random.Random:
    # Stable per-campaign, per-mission generator (do NOT use built-in hash())
    mix = int(seed) ^ _stable_str_hash(mission_id) ^ 0xCACE01
    return random.Random(mix)


def generate_mission_caches(seed: int, mission_id: str) -> list[dict]:
    """
    Spawn only materials belonging to mission_id.
    World caches provide a portion of required qty; procurement covers the rest.
    """
    reqs = mats.required_quantities_for_mission(mission_id)
    if not reqs:
        return []
    rng = _mission_rng(seed, mission_id)
    sites = CANDIDATE_SITES[:]
    rng.shuffle(sites)
    caches: list[dict] = []
    site_i = 0

    # Guarantee at least one cache opportunity for each mandatory material,
    # but never more than the required quantity total across caches.
    # Guarantee at least one world unit of every mandatory material so research is never required
    for mid, need in reqs.items():
        world_qty = max(1, min(int(need), 1))
        if site_i >= len(sites):
            break
        pos = sites[site_i]
        site_i += 1
        uid = f"cache_{seed}_{mission_id}_{mid}"
        caches.append(
            {
                "uid": uid,
                "material": mid,
                "qty": world_qty,
                "pos": list(pos),
                "mission": mission_id,
                "active": True,
                "name": f"Supply Cache ({mats.CATALOG[mid]['name']})",
            }
        )

    # Optional research log only for mission_1 (clue, not mandatory)
    if mission_id == "mission_1" and site_i < len(sites) and rng.random() < 0.5:
        pos = sites[site_i]
        uid = f"cache_{seed}_{mission_id}_research_log"
        caches.append(
            {
                "uid": uid,
                "material": "research_log",
                "qty": 1,
                "pos": list(pos),
                "mission": mission_id,
                "active": True,
                "name": f"Supply Cache ({mats.CATALOG['research_log']['name']})",
            }
        )
    return caches


def generate_caches(seed: int, count: int = 6) -> list[dict]:
    """Backward-compatible helper — Mission 1 pool only."""
    return generate_mission_caches(seed, "mission_1")[:count]


def apply_caches_to_colony(colony: dict, cache_records: list[dict]) -> None:
    """Add active cache collectibles into colony interactables (idempotent by uid)."""
    existing = {c["id"] for c in colony.get("collectibles", [])}
    for rec in cache_records:
        if not rec.get("active", True):
            continue
        if rec["uid"] in existing:
            continue
        if rec.get("material") not in mats.CATALOG:
            continue
        col = interactions.make_collectible(
            rec["uid"],
            rec["name"],
            tuple(rec["pos"]),
            mats.CATALOG[rec["material"]]["category"],
            f"E - Collect {mats.CATALOG[rec['material']]['name']}",
            (255, 200, 90),
            radius=58,
        )
        col["material"] = rec["material"]
        col["qty"] = rec["qty"]
        col["cache"] = True
        col["mission"] = rec.get("mission")
        colony["collectibles"].append(col)
        colony["interactables"].append(col)


def apply_fixed_mission_pickups(colony: dict, mission_id: str, collected_ids: set[str] | None = None) -> None:
    """Add fixed WORLD_PICKUPS for the active mission only."""
    collected_ids = collected_ids or set()
    existing = {c["id"] for c in colony.get("collectibles", [])}
    for pickup in mats.world_pickups_for_mission(mission_id):
        if pickup["uid"] in existing:
            continue
        info = mats.CATALOG[pickup["material"]]
        col = interactions.make_collectible(
            pickup["uid"],
            info["name"],
            pickup["pos"],
            info["category"],
            f"E - Collect {info['name']}",
            (90, 220, 160) if info["mandatory"] else (160, 200, 230),
            radius=60,
        )
        col["material"] = pickup["material"]
        col["qty"] = pickup["qty"]
        col["mission"] = mission_id
        if pickup["uid"] in collected_ids:
            col["collected"] = True
            col["status"] = "collected"
        colony["collectibles"].append(col)
        colony["interactables"].append(col)


def strip_non_mission_material_pickups(colony: dict) -> None:
    """Remove legacy all-mission WORLD_PICKUPS that were baked into make_colony."""
    keep_collect = []
    for c in colony.get("collectibles", []):
        mid = c.get("material")
        # Keep flavor samples without materials; drop material pickups (re-added per mission)
        if mid and mid in mats.CATALOG:
            continue
        keep_collect.append(c)
    colony["collectibles"] = keep_collect
    stations = [x for x in colony.get("interactables", []) if x.get("type") == "station"]
    colony["interactables"] = stations + keep_collect


def mark_collected(campaign: dict, uid: str) -> None:
    ids = campaign.setdefault("collected_cache_ids", [])
    if uid not in ids:
        ids.append(uid)


def restore_collected_flags(colony: dict, campaign: dict) -> None:
    collected = set(campaign.get("collected_cache_ids") or [])
    for col in colony.get("collectibles", []):
        if col.get("id") in collected:
            col["collected"] = True
            col["status"] = "collected"


def ensure_campaign_caches(campaign: dict) -> list[dict]:
    """Ensure caches exist for the current unlocked incomplete mission."""
    from systems import campaign as camp

    records = campaign.get("randomized_cache_records")
    if not isinstance(records, list):
        records = []
        campaign["randomized_cache_records"] = records

    # Migrate legacy mixed pools: keep only if they have mission tags matching unlocked set
    if records and not any(r.get("mission") for r in records):
        # Old format — replace with mission-specific for active mission only
        mid = camp.active_mission_id(campaign) or "mission_1"
        records = generate_mission_caches(campaign["campaign_seed"], mid)
        campaign["randomized_cache_records"] = records

    active = camp.active_mission_id(campaign)
    if active:
        has_active = any(r.get("mission") == active and r.get("active", True) for r in records)
        if not has_active and active not in campaign.get("completed_missions", []):
            records.extend(generate_mission_caches(campaign["campaign_seed"], active))
            campaign["randomized_cache_records"] = records

    _sync_cache_maps(campaign)
    return campaign["randomized_cache_records"]


def on_mission_completed(campaign: dict, completed_id: str, next_id: str | None) -> None:
    """Deactivate completed mission caches; generate next mission pool."""
    for rec in campaign.get("randomized_cache_records") or []:
        if rec.get("mission") == completed_id:
            rec["active"] = False
    if next_id:
        existing = [
            r for r in (campaign.get("randomized_cache_records") or [])
            if r.get("mission") == next_id
        ]
        if not existing:
            campaign.setdefault("randomized_cache_records", []).extend(
                generate_mission_caches(campaign["campaign_seed"], next_id)
            )
    _sync_cache_maps(campaign)


def reconcile_after_purchase(campaign: dict, material_id: str, owned: int, required: int) -> None:
    """
    If purchase covers remaining need, deactivate redundant uncollected caches
    for that material on the active mission.
    """
    if owned < required:
        return
    collected = set(campaign.get("collected_cache_ids") or [])
    for rec in campaign.get("randomized_cache_records") or []:
        if not rec.get("active", True):
            continue
        if rec.get("material") != material_id:
            continue
        if rec.get("uid") in collected:
            continue
        # Secured via procurement — deactivate world farm
        rec["active"] = False
        rec["secured_via_procurement"] = True
    _sync_cache_maps(campaign)


def refresh_colony_supplies(colony: dict, campaign: dict) -> None:
    """Rebuild mission-specific world supplies from campaign state."""
    from systems import campaign as camp

    strip_non_mission_material_pickups(colony)
    collected = set(campaign.get("collected_cache_ids") or [])
    active = camp.active_mission_id(campaign)
    if active:
        apply_fixed_mission_pickups(colony, active, collected)
    # Only active caches for unlocked incomplete missions
    active_recs = [
        r for r in (campaign.get("randomized_cache_records") or [])
        if r.get("active", True)
        and r.get("mission") in (campaign.get("unlocked_missions") or [])
        and r.get("mission") not in (campaign.get("completed_missions") or [])
    ]
    apply_caches_to_colony(colony, active_recs)
    restore_collected_flags(colony, campaign)


def _sync_cache_maps(campaign: dict) -> None:
    locs = {}
    contents = {}
    for rec in campaign.get("randomized_cache_records") or []:
        uid = rec.get("uid")
        if not uid:
            continue
        locs[uid] = list(rec.get("pos") or [0, 0])
        contents[uid] = {
            "material": rec.get("material"),
            "qty": rec.get("qty", 1),
            "mission": rec.get("mission"),
            "active": rec.get("active", True),
        }
    campaign["material_cache_locations"] = locs
    campaign["material_cache_contents"] = contents
