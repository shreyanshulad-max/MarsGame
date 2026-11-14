"""Connected Mars outpost simulation — life support, radiation, power, food.

Simulated game indices only. Not NASA engineering specifications.
Extends the existing campaign dict (no second economy / inventory).
"""

from __future__ import annotations

from copy import deepcopy

# Fictional game thresholds (labelled as simulation indices in UI)
POWER_BUDGET = 80

SYSTEM_KEYS = ("life_support", "radiation", "power", "food")

DEFAULT_ALLOCATION = {
    "life_support": 25,
    "food": 15,
    "comms": 15,
    "thermal": 15,
    "lighting": 10,
}

MIN_REQUIREMENTS = {
    "life_support": 20,
    "food": 10,
    "comms": 10,
    "thermal": 10,
    "lighting": 5,
}


def default_outpost() -> dict:
    return {
        "life_support": {
            "oxygen_circulation": 70.0,      # simulation index 0–100
            "habitat_stability": 70.0,
            "power_ok": True,
            "warning": "",
        },
        "radiation": {
            "shielding_config": "baseline",  # baseline | polymer | regolith_sim
            "protection_index": 40.0,        # simulation index — NOT real dose
            "exposure_risk_index": 55.0,
            "notes": "Educational shielding design activity.",
        },
        "power": {
            "budget": POWER_BUDGET,
            "available": POWER_BUDGET,
            "allocation": dict(DEFAULT_ALLOCATION),
            "confirmed": False,
            "dust_event": False,
            "generation_factor": 1.0,  # reduced by dust events
        },
        "food": {
            "crop": "leafy_green_sim",
            "growth": 0.0,              # 0–100
            "water": 60.0,
            "nutrients": 60.0,
            "lighting_power_ok": False,
            "harvested": False,
            "status": "IDLE",
        },
        "log": [],
    }


def ensure_outpost(campaign: dict) -> dict:
    if not isinstance(campaign.get("outpost"), dict):
        campaign["outpost"] = default_outpost()
    op = campaign["outpost"]
    base = default_outpost()
    for key in SYSTEM_KEYS:
        if key not in op or not isinstance(op[key], dict):
            op[key] = deepcopy(base[key])
        else:
            for k, v in base[key].items():
                op[key].setdefault(k, deepcopy(v) if isinstance(v, (dict, list)) else v)
    op.setdefault("log", [])
    return op


def effective_budget(outpost: dict) -> int:
    p = outpost["power"]
    return max(0, int(round(p["budget"] * float(p.get("generation_factor", 1.0)))))


def allocation_total(outpost: dict) -> int:
    return sum(int(v) for v in outpost["power"]["allocation"].values())


def can_set_allocation(outpost: dict, system: str, value: int) -> tuple[bool, str]:
    if system not in outpost["power"]["allocation"]:
        return False, "Unknown system."
    value = int(value)
    if value < 0:
        return False, "Allocation cannot be negative."
    trial = dict(outpost["power"]["allocation"])
    trial[system] = value
    if sum(trial.values()) > effective_budget(outpost):
        return False, "Total exceeds available power budget."
    return True, "OK"


def set_allocation(outpost: dict, system: str, value: int) -> tuple[bool, str]:
    ok, msg = can_set_allocation(outpost, system, value)
    if not ok:
        return False, msg
    outpost["power"]["allocation"][system] = int(value)
    outpost["power"]["confirmed"] = False
    _recompute(outpost)
    return True, f"{system} set to {int(value)}"


def adjust_allocation(outpost: dict, system: str, delta: int) -> tuple[bool, str]:
    cur = int(outpost["power"]["allocation"].get(system, 0))
    return set_allocation(outpost, system, cur + int(delta))


def confirm_allocation(outpost: dict) -> tuple[bool, str]:
    total = allocation_total(outpost)
    budget = effective_budget(outpost)
    if total > budget:
        return False, f"Over budget ({total}/{budget})."
    outpost["power"]["confirmed"] = True
    _recompute(outpost)
    _log(outpost, f"Power allocation confirmed ({total}/{budget}).")
    return True, "Allocation confirmed."


def apply_dust_event(outpost: dict, active: bool = True) -> None:
    outpost["power"]["dust_event"] = bool(active)
    outpost["power"]["generation_factor"] = 0.7 if active else 1.0
    _recompute(outpost)
    _log(outpost, "Dust event reduced solar generation." if active else "Dust event cleared.")


def set_shielding(outpost: dict, config_id: str) -> tuple[bool, str]:
    configs = {
        "baseline": (40.0, 55.0, "Minimal simulated habitat shell."),
        "polymer": (62.0, 38.0, "Added polymer layer (simulation index)."),
        "regolith_sim": (78.0, 25.0, "Regolith berm analogue (simulation index)."),
    }
    if config_id not in configs:
        return False, "Unknown shielding configuration."
    prot, risk, note = configs[config_id]
    outpost["radiation"]["shielding_config"] = config_id
    outpost["radiation"]["protection_index"] = prot
    outpost["radiation"]["exposure_risk_index"] = risk
    outpost["radiation"]["notes"] = note
    _log(outpost, f"Shielding set to {config_id} (simulation indices only).")
    return True, note


def tick_greenhouse(outpost: dict, dt: float) -> None:
    """Advance simplified crop growth when conditions are met."""
    food = outpost["food"]
    if food.get("harvested"):
        food["status"] = "HARVESTED"
        return
    power_ok = outpost["power"]["allocation"].get("food", 0) >= MIN_REQUIREMENTS["food"]
    food["lighting_power_ok"] = power_ok and outpost["power"].get("confirmed", False)
    water_ok = food.get("water", 0) >= 40
    nutrient_ok = food.get("nutrients", 0) >= 40
    if food["lighting_power_ok"] and water_ok and nutrient_ok:
        food["growth"] = min(100.0, float(food["growth"]) + dt * 4.0)
        food["status"] = "GROWING"
        food["water"] = max(0.0, float(food["water"]) - dt * 0.4)
        food["nutrients"] = max(0.0, float(food["nutrients"]) - dt * 0.3)
    elif not food["lighting_power_ok"]:
        food["status"] = "NEEDS POWER"
    else:
        food["status"] = "NEEDS RESOURCES"
    if food["growth"] >= 100.0 and not food["harvested"]:
        food["status"] = "READY"


def harvest_crop(outpost: dict) -> tuple[bool, str]:
    food = outpost["food"]
    if food.get("harvested"):
        return False, "Already harvested."
    if food.get("growth", 0) < 100:
        return False, "Crop not ready."
    food["harvested"] = True
    food["status"] = "HARVESTED"
    _log(outpost, "Greenhouse crop harvested (simulation).")
    return True, "Harvest complete."


def refill_greenhouse(outpost: dict, water: float = 20, nutrients: float = 20) -> None:
    food = outpost["food"]
    food["water"] = min(100.0, float(food.get("water", 0)) + water)
    food["nutrients"] = min(100.0, float(food.get("nutrients", 0)) + nutrients)


def on_comm_restored(outpost: dict) -> None:
    _log(outpost, "Communications restored — Mission Control assistance online.")


def on_power_restored(outpost: dict, allocation: dict | None = None) -> None:
    if allocation:
        # Map CH2 life/food/comms extras into outpost allocation hints
        life = max(MIN_REQUIREMENTS["life_support"], int(allocation.get("life", 25)))
        food = max(MIN_REQUIREMENTS["food"], int(allocation.get("food", 15)))
        comms = max(MIN_REQUIREMENTS["comms"], int(allocation.get("comms", 15)))
        # Keep within budget with residual thermal/lighting
        rem = effective_budget(outpost) - (life + food + comms)
        thermal = max(MIN_REQUIREMENTS["thermal"], min(20, rem // 2))
        lighting = max(0, rem - thermal)
        outpost["power"]["allocation"] = {
            "life_support": life,
            "food": food,
            "comms": comms,
            "thermal": thermal,
            "lighting": lighting,
        }
    outpost["power"]["confirmed"] = True
    _recompute(outpost)
    _log(outpost, "Habitat power restored — outpost systems updating.")


def on_rover_rescued(outpost: dict) -> None:
    _log(outpost, "Rover rescued — additional terrain research unlocked.")


def summary_lines(outpost: dict) -> list[str]:
    ls = outpost["life_support"]
    rad = outpost["radiation"]
    pwr = outpost["power"]
    food = outpost["food"]
    return [
        f"Life support  O₂ {int(ls['oxygen_circulation'])}  ·  Stability {int(ls['habitat_stability'])}",
        f"Radiation     Protection {int(rad['protection_index'])}  ·  Risk {int(rad['exposure_risk_index'])} (sim)",
        f"Power         {allocation_total(outpost)}/{effective_budget(outpost)} allocated"
        + ("  ·  DUST" if pwr.get("dust_event") else ""),
        f"Food          {food['status']}  ·  Growth {int(food['growth'])}%",
    ]


def _recompute(outpost: dict) -> None:
    alloc = outpost["power"]["allocation"]
    ls = outpost["life_support"]
    life_pwr = int(alloc.get("life_support", 0))
    need = MIN_REQUIREMENTS["life_support"]
    ls["power_ok"] = life_pwr >= need and outpost["power"].get("confirmed", False)
    if not outpost["power"].get("confirmed", False):
        ls["warning"] = "Confirm power allocation to stabilize life support."
    elif life_pwr < need:
        ls["oxygen_circulation"] = max(20.0, 50.0 - (need - life_pwr) * 2)
        ls["habitat_stability"] = max(20.0, 50.0 - (need - life_pwr) * 2.5)
        ls["warning"] = "Life support below minimum power — stability falling."
    else:
        ls["oxygen_circulation"] = min(100.0, 70.0 + (life_pwr - need) * 1.5)
        ls["habitat_stability"] = min(100.0, 70.0 + (life_pwr - need) * 1.2)
        ls["warning"] = ""

    # Thermal shortfall soft warning into stability
    if alloc.get("thermal", 0) < MIN_REQUIREMENTS["thermal"] and outpost["power"].get("confirmed"):
        ls["habitat_stability"] = max(15.0, ls["habitat_stability"] - 8)
        if not ls["warning"]:
            ls["warning"] = "Thermal power low — habitat stability reduced."

    outpost["power"]["available"] = max(0, effective_budget(outpost) - allocation_total(outpost))


def _log(outpost: dict, msg: str) -> None:
    outpost.setdefault("log", []).append(msg)
    if len(outpost["log"]) > 40:
        outpost["log"] = outpost["log"][-40:]
