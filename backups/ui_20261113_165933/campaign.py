"""Campaign progression — sequential missions, RP vs Mission Score, completion guards."""

from __future__ import annotations

import random
import time
from copy import deepcopy

MISSION_ORDER = ["mission_1", "mission_2", "mission_3"]

MISSION_META = {
    "mission_1": {
        "id": "mission_1",
        "name": "Communication Blackout",
        "short": "Restore antenna link (SAT-02)",
        "station": "comm",
        "screen": "ch1_diag",
        "kit": ["copper_wire", "signal_amplifier", "spare_fuse"],
        "points": 100,
        "unlocks_research_tier": 2,
    },
    "mission_2": {
        "id": "mission_2",
        "name": "Shelter Power Emergency",
        "short": "Rebuild habitat power circuit",
        "station": "power",
        "screen": "ch2_intro",
        "kit": ["insulated_cable", "spare_fuse"],
        "points": 100,
        "unlocks_research_tier": 3,
    },
    "mission_3": {
        "id": "mission_3",
        "name": "Rover Rescue",
        "short": "Repair and rescue the stranded rover",
        "station": "rover",
        "screen": "ch3_intro",
        "kit": ["servo_motor", "battery_cell", "lubricant", "metal_bracket"],
        "points": 100,
        "unlocks_research_tier": 3,
    },
}

STATUS_LOCKED = "LOCKED"
STATUS_AVAILABLE = "AVAILABLE"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_COMPLETED = "COMPLETED"

SAVE_VERSION = 1


def make_campaign(seed: int | None = None) -> dict:
    if seed is None:
        seed = random.randint(1, 2_000_000_000)
    return {
        "version": SAVE_VERSION,
        "campaign_seed": int(seed),
        "campaign_started": True,
        "campaign_completed": False,
        "current_campaign_stage": "mission_1",
        "completed_missions": [],
        "unlocked_missions": ["mission_1"],
        "mission_status": {
            "mission_1": STATUS_AVAILABLE,
            "mission_2": STATUS_LOCKED,
            "mission_3": STATUS_LOCKED,
        },
        "mission_completion_records": {},
        "research_tasks_completed": [],
        "research_task_rewards": {},  # task_id -> {rp, accuracy_bonus, first_bonus}
        "research_points": 0,
        "mission_score": 0,
        "research_tier": 1,
        "purchased_materials": {},  # mid -> qty purchased lifetime
        "inventory_stock": {},  # filled on sync
        "discovered_locations": [],
        "discovered_research_items": [],
        "randomized_cache_records": [],
        "procurement_state": {"offers": [], "bonus_stock": {}},
        "cross": {
            "comm_restored": False,
            "power_restored": False,
            "rover_rescued": False,
            "extra_life": 0,
            "extra_food": 0,
            "extra_comms": 0,
            "scan_clarity": 0.0,
        },
        "reward_log": [],  # recent breakdown lines
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def is_unlocked(campaign: dict, mission_id: str) -> bool:
    return mission_id in campaign.get("unlocked_missions", [])


def is_completed(campaign: dict, mission_id: str) -> bool:
    return mission_id in campaign.get("completed_missions", [])


def mission_status(campaign: dict, mission_id: str) -> str:
    if is_completed(campaign, mission_id):
        return STATUS_COMPLETED
    if not is_unlocked(campaign, mission_id):
        return STATUS_LOCKED
    return campaign.get("mission_status", {}).get(mission_id, STATUS_AVAILABLE)


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


def mark_in_progress(campaign: dict, mission_id: str) -> None:
    if is_completed(campaign, mission_id) or not is_unlocked(campaign, mission_id):
        return
    campaign["mission_status"][mission_id] = STATUS_IN_PROGRESS
    campaign["current_campaign_stage"] = mission_id
    _touch(campaign)


def complete_mission(campaign: dict, mission_id: str, report: dict) -> dict:
    """
    Permanently complete a mission once. Returns award summary.
    Guarded against duplicate rewards.
    """
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
    campaign["mission_score"] += points
    campaign["mission_completion_records"][mission_id] = {
        **report,
        "mission_id": mission_id,
        "name": meta["name"],
        "points_awarded": points,
        "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    campaign["reward_log"].append(f"+{points} Mission Score — {meta['name']} completed")
    if len(campaign["reward_log"]) > 40:
        campaign["reward_log"] = campaign["reward_log"][-40:]

    # Cross flags
    if mission_id == "mission_1":
        campaign["cross"]["comm_restored"] = True
        campaign["cross"]["scan_clarity"] = max(campaign["cross"].get("scan_clarity", 0), 0.45)
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
    elif mission_id == "mission_3":
        campaign["cross"]["rover_rescued"] = True
        campaign["campaign_completed"] = True
        campaign["current_campaign_stage"] = "final_report"

    # Unlock next + research tier
    campaign["research_tier"] = max(campaign.get("research_tier", 1), meta["unlocks_research_tier"])
    unlocked = None
    idx = MISSION_ORDER.index(mission_id)
    if idx + 1 < len(MISSION_ORDER):
        nxt = MISSION_ORDER[idx + 1]
        if nxt not in campaign["unlocked_missions"]:
            campaign["unlocked_missions"].append(nxt)
            campaign["mission_status"][nxt] = STATUS_AVAILABLE
            unlocked = nxt
            campaign["current_campaign_stage"] = nxt
            campaign["reward_log"].append(f"Unlocked: {MISSION_META[nxt]['name']}")

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
    """Award RP once per task. Returns breakdown."""
    if task_id in campaign["research_tasks_completed"]:
        return {
            "awarded": False,
            "rp": 0,
            "message": "Research already completed — no additional RP.",
            "breakdown": [],
        }
    total = max(0, int(base_rp) + int(accuracy_bonus) + int(first_bonus))
    campaign["research_tasks_completed"].append(task_id)
    campaign["research_points"] += total
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
    for line in breakdown:
        campaign["reward_log"].append(f"{line} ({task_id})")
    _touch(campaign)
    return {"awarded": True, "rp": total, "message": f"Earned {total} RP.", "breakdown": breakdown}


def spend_rp(campaign: dict, amount: int) -> bool:
    amount = int(amount)
    if amount < 0 or campaign["research_points"] < amount:
        return False
    campaign["research_points"] -= amount
    _touch(campaign)
    return True


def station_to_mission(station_id: str) -> str | None:
    for mid, meta in MISSION_META.items():
        if meta["station"] == station_id:
            return mid
    return None


def sync_status_flags(campaign: dict) -> tuple[str, str, str, str]:
    """Return communication, power, food, rover status strings for HUD."""
    comm = "ONLINE" if campaign["cross"].get("comm_restored") else "OFFLINE"
    power = "ONLINE" if campaign["cross"].get("power_restored") else "LOW"
    food = "SAFE" if campaign["cross"].get("power_restored") else "AT RISK"
    rover = "RESCUED" if campaign["cross"].get("rover_rescued") else "MISSING"
    return comm, power, food, rover


def _touch(campaign: dict) -> None:
    campaign["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")


def migrate(raw: dict) -> dict:
    """Preserve progress from older saves when possible."""
    base = make_campaign(raw.get("campaign_seed"))
    if not isinstance(raw, dict):
        return base
    ver = int(raw.get("version", 0))
    # Merge known keys
    for key in base:
        if key in raw:
            base[key] = raw[key]
    base["version"] = SAVE_VERSION
    # Ensure lists/dicts
    for k in ("completed_missions", "unlocked_missions", "research_tasks_completed", "reward_log", "randomized_cache_records"):
        if not isinstance(base.get(k), list):
            base[k] = []
    for k in ("mission_status", "mission_completion_records", "research_task_rewards", "purchased_materials", "procurement_state", "cross"):
        if not isinstance(base.get(k), dict):
            base[k] = make_campaign()[k] if k != "procurement_state" else {"offers": [], "bonus_stock": {}}
    if "mission_1" not in base["unlocked_missions"]:
        base["unlocked_missions"].insert(0, "mission_1")
    # Rebuild status from completed
    for mid in MISSION_ORDER:
        if mid in base["completed_missions"]:
            base["mission_status"][mid] = STATUS_COMPLETED
        elif mid in base["unlocked_missions"]:
            if base["mission_status"].get(mid) != STATUS_IN_PROGRESS:
                base["mission_status"][mid] = STATUS_AVAILABLE
        else:
            base["mission_status"][mid] = STATUS_LOCKED
    if ver < 1:
        base["reward_log"].append("Save migrated to campaign v1.")
    return base


def export_for_save(campaign: dict, inventory_stock: dict, discovery: dict | None = None) -> dict:
    data = deepcopy(campaign)
    data["inventory_stock"] = deepcopy(inventory_stock)
    if discovery:
        data["discovered_locations"] = list(discovery.get("landmarks", set()))
        data["discovery_revealed"] = list(discovery.get("revealed", set()))
        data["discovery_identified"] = list(discovery.get("identified", set()))
        data["discovery_scanned"] = list(discovery.get("scanned_ids", set()))
    return data
