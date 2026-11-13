"""Guidance arrow / objective priority smoke tests."""

from __future__ import annotations

import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from systems import campaign as camp
from systems import colony as colony_sys
from systems import guidance as guide
from systems import inventory as inv_sys
from systems import minimap as map_sys
from systems import materials as mats

ok = fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name} {detail}")


print("=== Guidance priority ===")
colony = colony_sys.make_colony("ch1_diag", "ch2_intro", "ch3_intro", "research", "shop")
discovery = map_sys.make_discovery(colony["spawn"])
inv = inv_sys.make_inventory()
c = camp.make_campaign(seed=7)

# Fresh campaign: missing kit, 0 RP → research
obj = guide.resolve_objective(c, inv, colony, discovery)
check("start → research", obj["kind"] == "research", obj)
check("research dest exact", obj["exact"] is True)
rx, ry = None, None
for st in colony["stations"]:
    if st["id"] == "research":
        rx, ry = st["pos"]
check("points at research station", abs(obj["x"] - rx) < 1 and abs(obj["y"] - ry) < 1)

# Enough RP, still missing → shop
c["research_points"] = 200
obj = guide.resolve_objective(c, inv, colony, discovery)
check("RP ready → shop", obj["kind"] == "shop", obj)
for st in colony["stations"]:
    if st["id"] == "shop":
        sx, sy = st["pos"]
check("points at shop", abs(obj["x"] - sx) < 1)

# Kit complete → mission 1 station (not locked m2/m3)
for mid in camp.MISSION_META["mission_1"]["kit"]:
    mats.add_material(inv["stock"], mid, 1)
obj = guide.resolve_objective(c, inv, colony, discovery)
check("kit ready → mission", obj["kind"] == "mission", obj)
check("mission 1 name", "Communication" in obj["title"], obj)
for st in colony["stations"]:
    if st["id"] == "comm":
        cx, cy = st["pos"]
check("points at comm", abs(obj["x"] - cx) < 1)
check("not locked rover", obj["dest_name"] != "Rover Rescue Station")

# Completed m1 → next unlocked is m2 (still missing kit → research/shop)
camp.complete_mission(c, "mission_1", {"summary": "ok"})
obj = guide.resolve_objective(c, inv, colony, discovery)
check("after m1 → not completed mission", obj["kind"] in ("research", "shop", "search", "supply"), obj)
check("not guiding to locked m3 station", "Rover" not in obj.get("dest_name", ""))

# Campaign complete → final
camp.complete_mission(c, "mission_2", {"summary": "ok"})
# give m3 kit
for mid in camp.MISSION_META["mission_3"]["kit"]:
    mats.add_material(inv["stock"], mid, 1)
c["research_points"] = 500
camp.complete_mission(c, "mission_3", {"summary": "ok"})
obj = guide.resolve_objective(c, inv, colony, discovery)
check("all done → final", obj["kind"] == "final", obj)

print("=== Undiscovered cache privacy ===")
c2 = camp.make_campaign(seed=99)
inv2 = inv_sys.make_inventory()
# Place a copper_wire cache that is NOT discovered
colony2 = colony_sys.make_colony("ch1_diag", "ch2_intro", "ch3_intro", "research", "shop")
disc2 = map_sys.make_discovery(colony2["spawn"])
# Inject fake undiscovered cache
fake = {
    "id": "cache_test_wire",
    "name": "Hidden Wire Cache",
    "pos": (9999, 9999),  # exact must NOT be used while unknown
    "type": "collectible",
    "kind": "supply",
    "material": "copper_wire",
    "collected": False,
    "status": "world",
}
colony2["collectibles"].append(fake)
c2["research_points"] = 0
obj = guide.resolve_objective(c2, inv2, colony2, disc2)
check("undiscovered → not exact coords", not (obj.get("exact") and abs(obj["x"] - 9999) < 1), obj)
# With RP but still prefer shop over revealing cache
c2["research_points"] = 500
obj = guide.resolve_objective(c2, inv2, colony2, disc2)
check("RP → shop not secret cache", obj["kind"] == "shop", obj)
# After discovery → exact
disc2["identified"].add("cache_test_wire")
obj = guide.resolve_objective(c2, inv2, colony2, disc2)
check("discovered → exact supply", obj["kind"] == "supply" and obj["exact"] and abs(obj["x"] - 9999) < 1, obj)

print("=== Arrow math / update ===")
g = guide.make_guidance()
check("enabled by default", g["enabled"] is True)
astro = {"x": 0.0, "y": 0.0, "facing": "down"}
obj = {"x": 100.0, "y": 0.0, "dest_name": "T", "title": "T", "task": "t", "exact": True, "kind": "mission", "icon": "mission"}
guide.update(g, 1.0, astro, obj, colliders=[])
check("angle toward +x ~0", abs(g["display_angle"]) < 5 or abs(g["display_angle"] - 360) < 5, g["display_angle"])
obj2 = {"x": 0.0, "y": 100.0, "dest_name": "T", "title": "T", "task": "t", "exact": True, "kind": "mission", "icon": "mission"}
guide.update(g, 1.0, astro, obj2, colliders=[])
check("angle toward +y ~90", abs(g["display_angle"] - 90) < 5, g["display_angle"])
# Obstacle detour
wall = pygame.Rect(40, -20, 20, 40)
wx, wy, detour = guide.compute_waypoint(astro, obj, [wall])
check("detour around wall", detour is True, (wx, wy))
wx2, wy2, detour2 = guide.compute_waypoint(astro, obj, [])
check("clear path no detour", detour2 is False and wx2 == 100)

print("=== Labels / map sync helper ===")
lbl = guide.objective_label(obj)
check("label non-empty", len(lbl) > 5)

print(f"\nResult: {ok} passed, {fail} failed")
sys.exit(0 if fail == 0 else 1)
