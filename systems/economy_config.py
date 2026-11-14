"""Central economy configuration — RP rewards and procurement prices."""

from __future__ import annotations

# Research Point rewards (base). Accuracy bonuses are optional extras in task defs.
RESEARCH_BASE_RP = 30

# Mandatory kit prices per material — totals must be <= 90 RP per research tier.
PROCUREMENT_PRICES = {
    # Mission 1 kit total: 25+35+20 = 80 RP (<= 90)
    "copper_wire": 25,
    "signal_amplifier": 35,
    "spare_fuse": 20,
    # Mission 2 kit: insulated_cable + spare_fuse = 30+20 = 50 (spare may already be owned)
    "insulated_cable": 30,
    "battery_cell": 25,
    # Mission 3 kit: 30+25+15+15 = 85 RP
    "servo_motor": 30,
    "lubricant": 15,
    "metal_bracket": 15,
}

MISSION_KIT_BUDGET_RP = {
    "mission_1": 80,
    "mission_2": 50,
    "mission_3": 85,
}

CURRENCY_ID = "RESEARCH_POINTS"
CURRENCY_LABEL = "RP"
