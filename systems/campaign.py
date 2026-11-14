"""Campaign progression — sequential missions, RP vs Mission Score, clearance, readiness."""

from __future__ import annotations

import random
import time
import uuid
from copy import deepcopy

# Canonical IDs (spec) mapped to internal keys used throughout the game
MISSION_1_COMMUNICATION = "mission_1"
MISSION_2_POWER = "mission_2"
MISSION_3_ROVER = "mission_3"

MISSION_ORDER = [MISSION_1_COMMUNICATION, MISSION_2_POWER, MISSION_3_ROVER]

CANONICAL_IDS = {
    "mission_1": "MISSION_1_COMMUNICATION",
    "mission_2": "MISSION_2_POWER",
    "mission_3": "MISSION_3_ROVER",
}

MISSION_META = {
    "mission_1": {
        "id": "mission_1",
        "canonical_id": "MISSION_1_COMMUNICATION",
        "name": "Communication Blackout",
        "short": "Restore antenna link (SAT-02)",
        "station": "comm",
        "screen": "ch1_diag",
        "kit": ["copper_wire", "signal_amplifier", "spare_fuse"],
        "points": 100,
        "unlocks_research_tier": 2,
        "research_clearance_key": "mission_1",
    },
    "mission_2": {
        "id": "mission_2",
        "canonical_id": "MISSION_2_POWER",
        "name": "Shelter Power Emergency",
        "short": "Rebuild habitat power circuit",
        "station": "power",
        "screen": "ch2_intro",
        "kit": ["insulated_cable", "spare_fuse"],
        "points": 100,
        "unlocks_research_tier": 3,
        "research_clearance_key": "mission_2",
    },
    "mission_3": {
        "id": "mission_3",
        "canonical_id": "MISSION_3_ROVER",
        "name": "Rover Rescue",
        "short": "Repair and rescue the stranded rover",
        "station": "rover",
        "screen": "ch3_intro",
        "kit": ["servo_motor", "battery_cell", "lubricant", "metal_bracket"],
        "points": 100,
        "unlocks_research_tier": 3,
        "research_clearance_key": "mission_3",
    },
}

# Core research tasks required for each mission's procurement clearance
CLEARANCE_TASKS = {
    "mission_1": ["res_1a_hirise", "res_1b_mola", "res_1c_site"],
    "mission_2": ["res_2a_meda", "res_2b_themis", "res_2c_solar"],
    "mission_3": ["res_3a_perc", "res_3b_hirise_dtm", "res_3c_mola_route"],
}

STATUS_LOCKED = "LOCKED"
STATUS_AVAILABLE = "AVAILABLE"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_COMPLETED = "COMPLETED"
STATUS_PREPARED = "PREPARED"

SAVE_VERSION = 3
SCHEMA_VERSION = 3


def make_campaign(seed: int | None = None) -> dict:
    if seed is None:
        seed = random.randint(1, 2_000_000_000)
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    from systems import outpost as op_sys

    data = {
        "schema_version": SCHEMA_VERSION,
        "version": SAVE_VERSION,
        "campaign_id": str(uuid.uuid4()),
        "campaign_seed": int(seed),
        "campaign_created_at": now,
        "created_at": now,
        "last_saved_at": now,
        "updated_at": now,
        "total_play_time": 0.0,
        "campaign_started": True,
        "campaign_completed": False,
        "current_campaign_stage": "mission_1",
        "active_mission_id": "mission_1",
        "current_objective_id": "prep_mission_1",
        "completed_missions": [],
        "unlocked_missions": ["mission_1"],
        "mission_states": {
            "mission_1": STATUS_AVAILABLE,
            "mission_2": STATUS_LOCKED,
            "mission_3": STATUS_LOCKED,
        },
        "mission_status": {
            "mission_1": STATUS_AVAILABLE,
            "mission_2": STATUS_LOCKED,
            "mission_3": STATUS_LOCKED,
        },
        "mission_reports": {},
        "mission_completion_records": {},
        "research_tasks": {},
        "research_tasks_completed": [],
        "research_task_rewards": {},
        "research_points": 0,
        "mission_score": 0,
        "research_tier": 1,
        "research_clearance": {
            "mission_1": False,
            "mission_2": False,
            "mission_3": False,
        },
        "purchased_materials": {},
        "material_purchases": {},
        "inventory_stock": {},
        "discovered_locations": [],
        "discovered_research_items": [],
        "material_cache_locations": {},
        "material_cache_contents": {},
        "randomized_cache_records": [],
        "collected_cache_ids": [],
        "procurement_state": {"offers": [], "bonus_stock": {}},
        "current_player_position": None,
        "replay_best": {},
        "cross": {
            "comm_restored": False,
            "power_restored": False,
            "rover_rescued": False,
            "extra_life": 0,
            "extra_food": 0,
            "extra_comms": 0,
            "scan_clarity": 0.0,
        },
        "reward_log": [],
        "outpost": None,  # filled by outpost.ensure_outpost
        "last_debrief_mission": None,
    }
    data["outpost"] = op_sys.default_outpost()
    return data


def is_unlocked(campaign: dict, mission_id: str) -> bool:
    return mission_id in campaign.get("unlocked_missions", [])


def is_completed(campaign: dict, mission_id: str) -> bool:
    return mission_id in campaign.get("completed_missions", [])


def mission_status(campaign: dict, mission_id: str) -> str:
    if is_completed(campaign, mission_id):
        return STATUS_COMPLETED
    if not is_unlocked(campaign, mission_id):
        return STATUS_LOCKED
    states = campaign.get("mission_status") or campaign.get("mission_states") or {}
    return states.get(mission_id, STATUS_AVAILABLE)


def lock_reason(campaign: dict, mission_id: str) -> str:
    if is_completed(campaign, mission_id):
        return "Mission completed."
    if is_unlocked(campaign, mission_id):
        return ""
    idx = MISSION_ORDER.index(mission_id) if mission_id in MISSION_ORDER else -1
    if idx <= 0:
        return "Unavailable."
    prev = MISSION_META[MISSION_ORDER[idx - 1]]["name"]
    return f"Locked — complete {prev} first."


def active_mission_id(campaign: dict) -> str | None:
    """First unlocked incomplete mission (current campaign focus)."""
    for mid in MISSION_ORDER:
        if is_completed(campaign, mid):
            continue
        if is_unlocked(campaign, mid):
            return mid
    return None


def research_clearance_granted(campaign: dict, mission_id: str) -> bool:
    refresh_research_clearance(campaign)
    return bool(campaign.get("research_clearance", {}).get(mission_id, False))


def refresh_research_clearance(campaign: dict) -> None:
    done = set(campaign.get("research_tasks_completed", []))
    clearance = campaign.setdefault("research_clearance", {})
    for mid, tasks in CLEARANCE_TASKS.items():
        clearance[mid] = all(t in done for t in tasks)


def material_owned(inventory_stock: dict, mid: str) -> int:
    slot = inventory_stock.get(mid, {"qty": 0})
    if isinstance(slot, dict):
        return int(slot.get("qty", 0))
    return int(slot or 0)


def kit_deficits(campaign: dict, inventory_stock: dict, mission_id: str) -> dict[str, int]:
    """Remaining quantity needed per kit material (required qty is 1 each)."""
    from systems import materials as mats

    reqs = mats.required_quantities_for_mission(mission_id)
    out = {}
    for mid, need in reqs.items():
        owned = material_owned(inventory_stock, mid)
        rem = max(0, need - owned)
        if rem:
            out[mid] = rem
    return out


def mission_materials_ready(campaign: dict, inventory_stock: dict, mission_id: str) -> bool:
    return not kit_deficits(campaign, inventory_stock, mission_id)


def mission_readiness(campaign: dict, inventory_stock: dict, mission_id: str) -> dict:
    """Explain exactly why a mission can or cannot start."""
    meta = MISSION_META.get(mission_id, {})
    st = mission_status(campaign, mission_id)
    result = {
        "mission_id": mission_id,
        "status": st,
        "can_start": False,
        "reasons": [],
        "research_done": [],
        "research_missing": [],
        "materials": {},
        "clearance": False,
    }
    if st == STATUS_COMPLETED:
        result["reasons"].append("Mission already completed — use Replay for practice.")
        return result
    if st == STATUS_LOCKED:
        result["reasons"].append(lock_reason(campaign, mission_id))
        return result

    tasks = CLEARANCE_TASKS.get(mission_id, [])
    done = set(campaign.get("research_tasks_completed", []))
    for tid in tasks:
        if tid in done:
            result["research_done"].append(tid)
        else:
            result["research_missing"].append(tid)
    clearance = research_clearance_granted(campaign, mission_id)
    result["clearance"] = clearance
    if not clearance:
        result["reasons"].append("Complete all mission research tasks for clearance.")

    from systems import materials as mats

    reqs = mats.required_quantities_for_mission(mission_id)
    deficits = kit_deficits(campaign, inventory_stock, mission_id)
    for mid, need in reqs.items():
        owned = material_owned(inventory_stock, mid)
        purchased = int(
            (campaign.get("material_purchases") or campaign.get("purchased_materials") or {}).get(mid, 0)
        )
        result["materials"][mid] = {
            "name": mats.CATALOG[mid]["name"],
            "required": need,
            "owned": owned,
            "purchased": purchased,
            "remaining": max(0, need - owned),
        }
    if deficits:
        names = [mats.CATALOG[m]["name"] for m in deficits]
        result["reasons"].append("Missing materials: " + ", ".join(names))

    if clearance and not deficits and st in (STATUS_AVAILABLE, STATUS_IN_PROGRESS, STATUS_PREPARED):
        result["can_start"] = True
    return result


def mark_in_progress(campaign: dict, mission_id: str) -> None:
    if is_completed(campaign, mission_id) or not is_unlocked(campaign, mission_id):
        return
    campaign["mission_status"][mission_id] = STATUS_IN_PROGRESS
    campaign["mission_states"][mission_id] = STATUS_IN_PROGRESS
    campaign["current_campaign_stage"] = mission_id
    campaign["active_mission_id"] = mission_id
    _touch(campaign)


def complete_mission(campaign: dict, mission_id: str, report: dict) -> dict:
    """Permanently complete a mission once. Returns award summary."""
    result = {"awarded": False, "mission_score": 0, "unlocked": None, "message": ""}
    if mission_id not in MISSION_META:
        result["message"] = "Unknown mission."
        return result
    if is_completed(campaign, mission_id):
        result["message"] = "Already completed — no additional rewards."
        return result
    if not is_unlocked(campaign, mission_id):
        result["message"] = "Mission is locked."
        return result

    meta = MISSION_META[mission_id]
    points = int(meta["points"])
    campaign["completed_missions"].append(mission_id)
    campaign["mission_status"][mission_id] = STATUS_COMPLETED
    campaign["mission_states"][mission_id] = STATUS_COMPLETED
    campaign["mission_score"] += points
    record = {
        **report,
        "mission_id": mission_id,
        "canonical_id": meta["canonical_id"],
        "name": meta["name"],
        "points_awarded": points,
        "materials_used": list(meta["kit"]),
        "research_discoveries": list(CLEARANCE_TASKS.get(mission_id, [])),
        "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    campaign["mission_completion_records"][mission_id] = record
    campaign["mission_reports"][mission_id] = record
    campaign["reward_log"].append(f"+{points} Mission Score — {meta['name']} completed")
    if len(campaign["reward_log"]) > 40:
        campaign["reward_log"] = campaign["reward_log"][-40:]

    from systems import outpost as op_sys

    op_sys.ensure_outpost(campaign)
    if mission_id == "mission_1":
        campaign["cross"]["comm_restored"] = True
        campaign["cross"]["scan_clarity"] = max(campaign["cross"].get("scan_clarity", 0), 0.45)
        op_sys.on_comm_restored(campaign["outpost"])
    elif mission_id == "mission_2":
        campaign["cross"]["power_restored"] = True
        extras = report.get("allocation_bonuses") or {}
        campaign["cross"]["extra_life"] = extras.get("extra_life", 0)
        campaign["cross"]["extra_food"] = extras.get("extra_food", 0)
        campaign["cross"]["extra_comms"] = extras.get("extra_comms", 0)
        campaign["cross"]["scan_clarity"] = min(
            1.0,
            campaign["cross"].get("scan_clarity", 0) + extras.get("extra_comms", 0) / 25.0,
        )
        # Map CH2 board values into outpost when provided
        ch2_alloc = report.get("power_allocation") or {
            "life": 20 + int(extras.get("extra_life", 0)),
            "food": 15 + int(extras.get("extra_food", 0)),
            "comms": 15 + int(extras.get("extra_comms", 0)),
        }
        op_sys.on_power_restored(campaign["outpost"], ch2_alloc)
    elif mission_id == "mission_3":
        campaign["cross"]["rover_rescued"] = True
        campaign["campaign_completed"] = True
        campaign["current_campaign_stage"] = "final_report"
        campaign["active_mission_id"] = None
        op_sys.on_rover_rescued(campaign["outpost"])
    campaign["last_debrief_mission"] = mission_id

    campaign["research_tier"] = max(campaign.get("research_tier", 1), meta["unlocks_research_tier"])
    unlocked = None
    idx = MISSION_ORDER.index(mission_id)
    if idx + 1 < len(MISSION_ORDER):
        nxt = MISSION_ORDER[idx + 1]
        if nxt not in campaign["unlocked_missions"]:
            campaign["unlocked_missions"].append(nxt)
            campaign["mission_status"][nxt] = STATUS_AVAILABLE
            campaign["mission_states"][nxt] = STATUS_AVAILABLE
            unlocked = nxt
            campaign["current_campaign_stage"] = nxt
            campaign["active_mission_id"] = nxt
            campaign["reward_log"].append(f"Unlocked: {MISSION_META[nxt]['name']}")

    # Deactivate completed-mission caches; generate next mission caches
    from systems import caches as cache_sys

    cache_sys.on_mission_completed(campaign, mission_id, unlocked)

    result.update(
        {
            "awarded": True,
            "mission_score": points,
            "unlocked": unlocked,
            "message": f"{meta['name']} complete. +{points} Mission Score.",
        }
    )
    _touch(campaign)
    return result


def award_research(
    campaign: dict,
    task_id: str,
    base_rp: int,
    accuracy_bonus: int = 0,
    first_bonus: int = 0,
) -> dict:
    """Award RP once per task. Returns breakdown. RP never goes negative via this path."""
    if task_id in campaign["research_tasks_completed"]:
        return {
            "awarded": False,
            "rp": 0,
            "message": "Research already completed — no additional RP.",
            "breakdown": [],
        }
    total = max(0, int(base_rp) + int(accuracy_bonus) + int(first_bonus))
    campaign["research_tasks_completed"].append(task_id)
    campaign["research_points"] = max(0, int(campaign.get("research_points", 0)) + total)
    breakdown = [f"+{base_rp} RP base"]
    if accuracy_bonus:
        breakdown.append(f"+{accuracy_bonus} RP accuracy")
    if first_bonus:
        breakdown.append(f"+{first_bonus} RP first completion")
    campaign["research_task_rewards"][task_id] = {
        "base": base_rp,
        "accuracy_bonus": accuracy_bonus,
        "first_bonus": first_bonus,
        "total": total,
    }
    campaign.setdefault("research_tasks", {})[task_id] = {
        "completed": True,
        "total_rp": total,
        "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    for line in breakdown:
        campaign["reward_log"].append(f"{line} ({task_id})")
    refresh_research_clearance(campaign)
    _touch(campaign)
    return {"awarded": True, "rp": total, "message": f"Earned {total} RP.", "breakdown": breakdown}


def spend_rp(campaign: dict, amount: int) -> bool:
    amount = int(amount)
    if amount < 0 or campaign["research_points"] < amount:
        return False
    campaign["research_points"] -= amount
    campaign["research_points"] = max(0, campaign["research_points"])
    _touch(campaign)
    return True


def station_to_mission(station_id: str) -> str | None:
    for mid, meta in MISSION_META.items():
        if meta["station"] == station_id:
            return mid
    return None


def sync_status_flags(campaign: dict) -> tuple[str, str, str, str]:
    comm = "ONLINE" if campaign["cross"].get("comm_restored") else "OFFLINE"
    power = "ONLINE" if campaign["cross"].get("power_restored") else "LOW"
    food = "SAFE" if campaign["cross"].get("power_restored") else "AT RISK"
    rover = "RESCUED" if campaign["cross"].get("rover_rescued") else "MISSING"
    return comm, power, food, rover


def _touch(campaign: dict) -> None:
    campaign["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    campaign["last_saved_at"] = campaign["updated_at"]


def archive_record(campaign: dict) -> dict:
    return {
        "campaign_id": campaign.get("campaign_id"),
        "campaign_seed": campaign.get("campaign_seed"),
        "completion_status": "completed" if campaign.get("campaign_completed") else "abandoned",
        "final_mission_score": campaign.get("mission_score", 0),
        "research_points": campaign.get("research_points", 0),
        "missions_completed": list(campaign.get("completed_missions", [])),
        "total_play_time": campaign.get("total_play_time", 0),
        "completion_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "created_at": campaign.get("campaign_created_at") or campaign.get("created_at"),
    }


def begin_replay(campaign: dict, mission_id: str) -> dict:
    """Snapshot permanent campaign fields for practice isolation."""
    return {
        "mode": "replay",
        "mission_id": mission_id,
        "snapshot": {
            "research_points": campaign.get("research_points", 0),
            "mission_score": campaign.get("mission_score", 0),
            "completed_missions": list(campaign.get("completed_missions", [])),
            "unlocked_missions": list(campaign.get("unlocked_missions", [])),
            "research_tasks_completed": list(campaign.get("research_tasks_completed", [])),
            "research_clearance": deepcopy(campaign.get("research_clearance", {})),
            "purchased_materials": deepcopy(campaign.get("purchased_materials", {})),
            "material_purchases": deepcopy(campaign.get("material_purchases", {})),
            "randomized_cache_records": deepcopy(campaign.get("randomized_cache_records", [])),
            "collected_cache_ids": list(campaign.get("collected_cache_ids", [])),
            "campaign_seed": campaign.get("campaign_seed"),
            "inventory_stock": deepcopy(campaign.get("inventory_stock", {})),
            "mission_status": deepcopy(campaign.get("mission_status", {})),
            "mission_states": deepcopy(campaign.get("mission_states", {})),
            "cross": deepcopy(campaign.get("cross", {})),
            "campaign_completed": campaign.get("campaign_completed", False),
            "current_campaign_stage": campaign.get("current_campaign_stage"),
            "active_mission_id": campaign.get("active_mission_id"),
            "research_tier": campaign.get("research_tier"),
            "reward_log": list(campaign.get("reward_log", [])),
        },
    }


def end_replay(campaign: dict, replay: dict) -> None:
    """Restore permanent campaign state after practice; discard temporary mutations."""
    snap = replay.get("snapshot") or {}
    for key, value in snap.items():
        campaign[key] = deepcopy(value) if isinstance(value, (dict, list)) else value
    _touch(campaign)


def practice_inventory_for(mission_id: str) -> dict:
    """Isolated practice stock with required kit components."""
    from systems import materials as mats
    from systems import inventory as inv_sys

    inv = inv_sys.make_inventory()
    reqs = mats.required_quantities_for_mission(mission_id)
    for mid, qty in reqs.items():
        mats.add_material(inv["stock"], mid, max(1, qty))
        inv["items"].append(
            {
                "id": f"practice_{mid}",
                "uid": f"practice_{mid}",
                "name": mats.CATALOG[mid]["name"],
                "kind": mats.CATALOG[mid]["category"],
                "material": mid,
                "qty": qty,
            }
        )
    return inv


def migrate(raw: dict) -> dict:
    """Preserve progress from older saves when possible."""
    if not isinstance(raw, dict):
        return make_campaign()
    base = make_campaign(raw.get("campaign_seed"))
    ver = int(raw.get("schema_version") or raw.get("version") or 0)

    for key in list(base.keys()):
        if key in raw:
            base[key] = raw[key]

    # Legacy aliases
    if "mission_status" in raw and isinstance(raw["mission_status"], dict):
        base["mission_status"] = dict(raw["mission_status"])
        base["mission_states"] = dict(raw["mission_status"])
    if "mission_states" in raw and isinstance(raw["mission_states"], dict):
        base["mission_states"] = dict(raw["mission_states"])
        if "mission_status" not in raw:
            base["mission_status"] = dict(raw["mission_states"])
    if "mission_completion_records" in raw:
        base["mission_completion_records"] = dict(raw["mission_completion_records"])
        if not raw.get("mission_reports"):
            base["mission_reports"] = dict(raw["mission_completion_records"])
    if "mission_reports" in raw and isinstance(raw["mission_reports"], dict):
        base["mission_reports"] = dict(raw["mission_reports"])
        if not base.get("mission_completion_records"):
            base["mission_completion_records"] = dict(raw["mission_reports"])
    if "purchased_materials" in raw:
        base["purchased_materials"] = dict(raw["purchased_materials"])
        if not raw.get("material_purchases"):
            base["material_purchases"] = dict(raw["purchased_materials"])
    if "material_purchases" in raw:
        base["material_purchases"] = dict(raw["material_purchases"])
        if not base.get("purchased_materials"):
            base["purchased_materials"] = dict(raw["material_purchases"])

    base["schema_version"] = SCHEMA_VERSION
    base["version"] = SAVE_VERSION
    if not base.get("campaign_id"):
        base["campaign_id"] = str(uuid.uuid4())
    if not base.get("campaign_created_at"):
        base["campaign_created_at"] = raw.get("created_at") or base["campaign_created_at"]

    for k in (
        "completed_missions",
        "unlocked_missions",
        "research_tasks_completed",
        "reward_log",
        "randomized_cache_records",
        "collected_cache_ids",
        "discovered_locations",
        "discovered_research_items",
    ):
        if not isinstance(base.get(k), list):
            base[k] = []

    for k in (
        "mission_status",
        "mission_states",
        "mission_completion_records",
        "mission_reports",
        "research_task_rewards",
        "research_tasks",
        "purchased_materials",
        "material_purchases",
        "research_clearance",
        "material_cache_locations",
        "material_cache_contents",
        "procurement_state",
        "cross",
        "replay_best",
    ):
        if not isinstance(base.get(k), dict):
            fresh = make_campaign()
            base[k] = fresh.get(k, {})

    if "mission_1" not in base["unlocked_missions"]:
        base["unlocked_missions"].insert(0, "mission_1")

    for mid in MISSION_ORDER:
        if mid in base["completed_missions"]:
            base["mission_status"][mid] = STATUS_COMPLETED
            base["mission_states"][mid] = STATUS_COMPLETED
        elif mid in base["unlocked_missions"]:
            if base["mission_status"].get(mid) != STATUS_IN_PROGRESS:
                base["mission_status"][mid] = STATUS_AVAILABLE
                base["mission_states"][mid] = STATUS_AVAILABLE
        else:
            base["mission_status"][mid] = STATUS_LOCKED
            base["mission_states"][mid] = STATUS_LOCKED

    # Normalize legacy research task IDs to current clearance IDs
    try:
        from systems import research_tasks as rtasks

        normalized = []
        for tid in base.get("research_tasks_completed") or []:
            task = rtasks.get_task(tid)
            if task:
                normalized.append(task["id"])
            else:
                normalized.append(tid)
        # Dedupe preserve order
        seen = set()
        uniq = []
        for tid in normalized:
            if tid not in seen:
                seen.add(tid)
                uniq.append(tid)
        base["research_tasks_completed"] = uniq
    except Exception:
        pass

    from systems import outpost as op_sys

    op_sys.ensure_outpost(base)
    refresh_research_clearance(base)
    if ver < 2:
        base["reward_log"].append("Save migrated to campaign schema v2.")
    if ver < 3:
        base["reward_log"].append("Save migrated to campaign schema v3 (outpost systems).")
    return base


def export_for_save(campaign: dict, inventory_stock: dict, discovery: dict | None = None) -> dict:
    data = deepcopy(campaign)
    data["schema_version"] = SCHEMA_VERSION
    data["version"] = SAVE_VERSION
    data["inventory_stock"] = deepcopy(inventory_stock)
    data["material_purchases"] = deepcopy(
        campaign.get("material_purchases") or campaign.get("purchased_materials") or {}
    )
    data["purchased_materials"] = deepcopy(data["material_purchases"])
    data["mission_states"] = deepcopy(campaign.get("mission_status") or campaign.get("mission_states") or {})
    data["mission_status"] = deepcopy(data["mission_states"])
    data["mission_reports"] = deepcopy(
        campaign.get("mission_reports") or campaign.get("mission_completion_records") or {}
    )
    data["mission_completion_records"] = deepcopy(data["mission_reports"])
    # Sync cache maps from records
    locs = {}
    contents = {}
    for rec in campaign.get("randomized_cache_records") or []:
        uid = rec.get("uid")
        if not uid:
            continue
        locs[uid] = list(rec.get("pos") or [0, 0])
        contents[uid] = {"material": rec.get("material"), "qty": rec.get("qty", 1), "mission": rec.get("mission")}
    data["material_cache_locations"] = locs
    data["material_cache_contents"] = contents
    if discovery:
        data["discovered_locations"] = list(discovery.get("landmarks", set()))
        data["discovery_revealed"] = list(discovery.get("revealed", set()))
        data["discovery_identified"] = list(discovery.get("identified", set()))
        data["discovery_scanned"] = list(discovery.get("scanned_ids", set()))
    refresh_research_clearance(data)
    return data
