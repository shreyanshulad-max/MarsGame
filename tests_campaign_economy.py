"""Automated campaign persistence / replay / economy tests (isolated temp save dir)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Isolate saves BEFORE importing savegame
_TMP = tempfile.mkdtemp(prefix="marsmission_test_")
os.environ["MARS_MISSION_SAVE_DIR"] = _TMP
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from systems import campaign as camp
from systems import caches
from systems import inventory as inv_sys
from systems import materials as mats
from systems import procurement as proc
from systems import research_data as rdata
from systems import research_tasks as rtasks
from systems import savegame


class CampaignEconomyTests(unittest.TestCase):
    def setUp(self):
        savegame.configure_paths(Path(os.environ["MARS_MISSION_SAVE_DIR"]))
        # Clean active save between tests
        for p in (savegame.SAVE_PATH, savegame.BACKUP_PATH):
            if p.is_file():
                p.unlink()

    def test_a_save_load_persistence(self):
        c = camp.make_campaign(seed=4242)
        camp.complete_mission(c, "mission_1", {"summary": "ok", "time_left": 12})
        inv = inv_sys.make_inventory()
        mats.add_material(inv["stock"], "spare_fuse", 1)
        caches.ensure_campaign_caches(c)
        self.assertTrue(savegame.save_campaign(camp.export_for_save(c, inv["stock"])))
        loaded = savegame.load_campaign()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["campaign_seed"], 4242)
        self.assertIn("mission_1", loaded["completed_missions"])
        self.assertIn("mission_2", loaded["unlocked_missions"])
        self.assertEqual(loaded["mission_score"], 100)
        self.assertEqual(loaded["inventory_stock"]["spare_fuse"]["qty"], 1)
        # Mission 1 must not be AVAILABLE again
        self.assertEqual(camp.mission_status(loaded, "mission_1"), camp.STATUS_COMPLETED)

    def test_b_replay_isolation(self):
        c = camp.make_campaign(seed=7)
        camp.complete_mission(c, "mission_1", {"summary": "done"})
        camp.award_research(c, "res_1a_hirise", 30, 0, 0)
        rp0, ms0 = c["research_points"], c["mission_score"]
        unlocked = list(c["unlocked_missions"])
        snap = camp.begin_replay(c, "mission_1")
        # Mutate as if replay awarded things
        c["research_points"] += 99
        c["mission_score"] += 50
        c["completed_missions"].append("mission_2")
        camp.end_replay(c, snap)
        self.assertEqual(c["research_points"], rp0)
        self.assertEqual(c["mission_score"], ms0)
        self.assertEqual(c["unlocked_missions"], unlocked)
        self.assertNotIn("mission_2", c["completed_missions"] if "mission_2" not in unlocked else c["completed_missions"])
        self.assertIn("mission_2", c["unlocked_missions"])

    def test_c_new_campaign_archive(self):
        c = camp.make_campaign(seed=11)
        camp.complete_mission(c, "mission_1", {"summary": "a"})
        camp.complete_mission(c, "mission_2", {"summary": "b", "allocation_bonuses": {}})
        camp.complete_mission(c, "mission_3", {"summary": "c"})
        savegame.save_campaign(camp.export_for_save(c, {}))
        new = savegame.archive_and_start_new(c, seed=99)
        self.assertEqual(new["campaign_seed"], 99)
        self.assertEqual(new["mission_score"], 0)
        self.assertEqual(new["research_points"], 0)
        self.assertEqual(new["completed_missions"], [])
        self.assertEqual(camp.mission_status(new, "mission_1"), camp.STATUS_AVAILABLE)
        self.assertEqual(camp.mission_status(new, "mission_2"), camp.STATUS_LOCKED)
        archive = savegame.load_archive()
        self.assertTrue(any(r.get("campaign_seed") == 11 for r in archive))
        # Reload new campaign locations stable
        caches.ensure_campaign_caches(new)
        locs = [tuple(r["pos"]) for r in new["randomized_cache_records"]]
        savegame.save_campaign(camp.export_for_save(new, {}))
        loaded = savegame.load_campaign()
        locs2 = [tuple(r["pos"]) for r in loaded["randomized_cache_records"]]
        self.assertEqual(locs, locs2)

    def test_d_randomized_mission_materials(self):
        c = camp.make_campaign(seed=555)
        caches.ensure_campaign_caches(c)
        mats_spawned = {r["material"] for r in c["randomized_cache_records"] if r.get("active", True)}
        pool = set(mats.material_pool_for_mission("mission_1")) | {"research_log"}
        self.assertTrue(mats_spawned.issubset(pool))
        self.assertNotIn("servo_motor", mats_spawned)
        self.assertNotIn("insulated_cable", mats_spawned)
        a = caches.generate_mission_caches(555, "mission_1")
        b = caches.generate_mission_caches(555, "mission_1")
        self.assertEqual(a, b)
        c2 = caches.generate_mission_caches(556, "mission_1")
        self.assertNotEqual(a, c2)
        # Collect persists
        uid = c["randomized_cache_records"][0]["uid"]
        caches.mark_collected(c, uid)
        savegame.save_campaign(camp.export_for_save(c, {}))
        loaded = savegame.load_campaign()
        self.assertIn(uid, loaded["collected_cache_ids"])
        # Complete m1 removes active m1 caches / generates m2
        camp.complete_mission(c, "mission_1", {"summary": "x"})
        self.assertTrue(any(r.get("mission") == "mission_2" for r in c["randomized_cache_records"]))
        for r in c["randomized_cache_records"]:
            if r.get("mission") == "mission_1":
                self.assertFalse(r.get("active", True))

    def test_e_research_rp_once(self):
        c = camp.make_campaign(1)
        t1 = [t for t in rtasks.TASKS.values() if t["tier"] == 1]
        self.assertEqual(len(t1), 3)
        self.assertEqual(sum(t["base_rp"] for t in t1), 90)
        a = camp.award_research(c, "res_1a_hirise", 30)
        self.assertTrue(a["awarded"])
        a2 = camp.award_research(c, "res_1a_hirise", 30)
        self.assertFalse(a2["awarded"])
        camp.award_research(c, "res_1b_mola", 30)
        camp.award_research(c, "res_1c_site", 30)
        camp.refresh_research_clearance(c)
        self.assertTrue(c["research_clearance"]["mission_1"])
        self.assertFalse(c["research_clearance"]["mission_2"])
        # Clearance for Mission 2 remains exactly three core tasks
        self.assertEqual(len(camp.CLEARANCE_TASKS["mission_2"]), 3)
        tier2_clearance = [rtasks.get_task(t) for t in camp.CLEARANCE_TASKS["mission_2"]]
        self.assertTrue(all(t and t["tier"] == 2 for t in tier2_clearance))

    def test_f_procurement_gates(self):
        c = camp.make_campaign(2)
        inv = inv_sys.make_inventory()
        c["research_points"] = 90
        ok, msg = proc.purchase(c, inv, "copper_wire", 1)
        self.assertFalse(ok)
        self.assertIn("Communication Research", msg)
        for tid in camp.CLEARANCE_TASKS["mission_1"]:
            camp.award_research(c, tid, 30)
        c["research_points"] = 10
        ok, msg = proc.purchase(c, inv, "copper_wire", 1)
        self.assertFalse(ok)
        self.assertIn("RP", msg)
        c["research_points"] = 90
        ok, msg = proc.purchase(c, inv, "copper_wire", 1)
        self.assertTrue(ok, msg)
        self.assertEqual(inv["stock"]["copper_wire"]["qty"], 1)
        ok2, msg2 = proc.purchase(c, inv, "copper_wire", 1)
        self.assertFalse(ok2)
        self.assertIn("secured", msg2.lower())
        # Future mission hidden
        ids = {it["id"] for it in proc.items_for_campaign(c)}
        self.assertNotIn("servo_motor", ids)
        self.assertIn("signal_amplifier", ids)

    def test_g_mission_readiness(self):
        c = camp.make_campaign(3)
        inv = inv_sys.make_inventory()
        ready = camp.mission_readiness(c, inv["stock"], "mission_1")
        self.assertFalse(ready["can_start"])
        for tid in camp.CLEARANCE_TASKS["mission_1"]:
            camp.award_research(c, tid, 30)
        ready = camp.mission_readiness(c, inv["stock"], "mission_1")
        self.assertFalse(ready["can_start"])
        for mid in mats.material_pool_for_mission("mission_1"):
            mats.add_material(inv["stock"], mid, 1)
        ready = camp.mission_readiness(c, inv["stock"], "mission_1")
        self.assertTrue(ready["can_start"])
        self.assertEqual(camp.mission_status(c, "mission_2"), camp.STATUS_LOCKED)
        # Locked mission cannot complete
        r = camp.complete_mission(c, "mission_2", {"summary": "no"})
        self.assertFalse(r["awarded"])

    def test_kit_costs_within_rp(self):
        for mid, budget in __import__("systems.economy_config", fromlist=["MISSION_KIT_BUDGET_RP"]).MISSION_KIT_BUDGET_RP.items():
            total = sum(
                proc.price_of(m) * q for m, q in mats.required_quantities_for_mission(mid).items()
            )
            self.assertLessEqual(total, 90, f"{mid} kit {total} > 90 RP")
            self.assertLessEqual(total, budget)

    def test_nasa_manifest_integrity(self):
        man = rdata.load_manifest()
        self.assertGreaterEqual(len(man["items"]), 5)
        for it in man["items"]:
            self.assertIsNot(it.get("fabricated"), True)
        solar = rdata.get_item(man, "solar_dust_spirit_01")
        self.assertTrue(rdata.item_available(solar))
        meda = rdata.get_item(man, "meda_timeline_01")
        self.assertTrue(rdata.item_available(meda))


if __name__ == "__main__":
    print(f"Using temp save dir: {_TMP}")
    result = unittest.main(verbosity=2, exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)
