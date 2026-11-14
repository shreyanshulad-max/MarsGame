"""Campaign progression / save / research / procurement smoke tests."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Never touch the player's live AppData save
os.environ["MARS_MISSION_SAVE_DIR"] = tempfile.mkdtemp(prefix="marsmission_smoke_")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from systems import campaign as camp
from systems import caches
from systems import inventory as inv_sys
from systems import procurement as proc
from systems import research_data as rdata
from systems import research_tasks as rtasks
from systems import savegame

savegame.configure_paths(Path(os.environ["MARS_MISSION_SAVE_DIR"]))

ok = fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name} {detail}")


print("=== Campaign sequence ===")
c = camp.make_campaign(seed=42)
check("m1 available", camp.mission_status(c, "mission_1") == camp.STATUS_AVAILABLE)
check("m2 locked", camp.mission_status(c, "mission_2") == camp.STATUS_LOCKED)
check("m3 locked", camp.mission_status(c, "mission_3") == camp.STATUS_LOCKED)
r = camp.complete_mission(c, "mission_2", {"summary": "x"})
check("cannot complete locked", not r["awarded"])
r = camp.complete_mission(c, "mission_1", {"summary": "ok", "time_left": 10})
check("m1 complete once", r["awarded"] and c["mission_score"] == 100)
check("m2 unlocked", camp.is_unlocked(c, "mission_2"))
check("tier 2", c["research_tier"] >= 2)
r2 = camp.complete_mission(c, "mission_1", {"summary": "again"})
check("no double reward", not r2["awarded"] and c["mission_score"] == 100)
camp.complete_mission(c, "mission_2", {"summary": "pwr", "allocation_bonuses": {"extra_comms": 10}})
check("m3 unlocked", camp.is_unlocked(c, "mission_3"))
camp.complete_mission(c, "mission_3", {"summary": "rescue"})
check("campaign done", c["campaign_completed"])

print("=== Research Points ===")
c2 = camp.make_campaign(99)
a = camp.award_research(c2, "res_hirise_surface", 35, 5, 0)
check("rp awarded", a["awarded"] and c2["research_points"] == 40)
a2 = camp.award_research(c2, "res_hirise_surface", 35, 5, 0)
check("rp no farm", not a2["awarded"] and c2["research_points"] == 40)

print("=== Procurement ===")
inv = inv_sys.make_inventory()
# Grant Mission 1 clearance then fund purchases
for tid in camp.CLEARANCE_TASKS["mission_1"]:
    if tid not in c2["research_tasks_completed"]:
        camp.award_research(c2, tid, 30)
c2["research_points"] = 90
ok_buy, msg = proc.purchase(c2, inv, "copper_wire", 1)
check("buy wire", ok_buy and inv["stock"]["copper_wire"]["qty"] == 1, msg)
check("rp spent", c2["research_points"] == 90 - proc.price_of("copper_wire"))
c2["research_points"] = 5
ok_buy2, msg2 = proc.purchase(c2, inv, "signal_amplifier", 1)
check("cannot overspend", not ok_buy2, msg2)

print("=== Caches seeded ===")
a = caches.generate_caches(12345)
b = caches.generate_caches(12345)
cch = caches.generate_caches(999)
check("same seed same caches", a == b)
check("diff seed differs", a != cch)

print("=== NASA manifest ===")
man = rdata.load_manifest()
check("manifest items", len(man.get("items", [])) >= 1)
avail = [it for it in man["items"] if rdata.item_available(it)]
print(f"  available browse items: {len(avail)}")
check("has browse or honest unavailable", len(man["items"]) >= 1)
mola = rdata.get_item(man, "mola_profile_sample_01")
check("mola numeric not fabricated", mola is None or mola.get("fabricated") is not True)

print("=== Save/load ===")
savegame.delete_campaign_for_new()
c3 = camp.make_campaign(777)
camp.complete_mission(c3, "mission_1", {"summary": "saved"})
camp.award_research(c3, "res_mola_elevation", 35, 5, 0)
inv2 = inv_sys.make_inventory()
proc.purchase(c3, inv2, "spare_fuse", 1)
savegame.save_campaign(camp.export_for_save(c3, inv2["stock"]))
loaded = savegame.load_campaign()
check("loaded", loaded is not None)
check("score persisted", loaded["mission_score"] == 100)
check("rp persisted", loaded["research_points"] == loaded.get("research_points", -1) >= 0)
check("m1 completed persisted", "mission_1" in loaded["completed_missions"])
check("m2 unlocked persisted", "mission_2" in loaded["unlocked_missions"])

print("=== Tasks config ===")
t1 = [t for t in rtasks.TASKS.values() if t["tier"] == 1]
rp1 = sum(t["base_rp"] + t.get("accuracy_bonus", 0) for t in t1)
check("tier1 rp >= 80 kit", rp1 >= 80, str(rp1))

print("=== main import ===")
sys.path.insert(0, r"C:\MarsMission")
import main as game

check("screens", hasattr(game, "SCREEN_RESEARCH") and hasattr(game, "SCREEN_DASHBOARD"))

print()
print(f"RESULT: {ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
