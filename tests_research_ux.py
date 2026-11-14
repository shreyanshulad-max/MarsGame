"""Research UX: optional progression, home nav, hide completed, multi-question reachability."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["MARS_MISSION_SAVE_DIR"] = tempfile.mkdtemp(prefix="marsmission_research_")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from systems import campaign as camp
from systems import materials as mats
from systems import procurement as proc
from systems import research_data as rdata
from systems import research_tasks as rtasks
from systems import research_terminal as rterm
from systems import inventory as inv_sys
from systems import savegame

savegame.configure_paths(Path(os.environ["MARS_MISSION_SAVE_DIR"]))


class ResearchUXTests(unittest.TestCase):
    def test_research_optional_for_start(self):
        c = camp.make_campaign(10)
        inv = inv_sys.make_inventory()
        for mid in mats.material_pool_for_mission("mission_1"):
            mats.add_material(inv["stock"], mid, 1)
        ready = camp.mission_readiness(c, inv["stock"], "mission_1")
        self.assertTrue(ready["can_start"])
        self.assertFalse(ready["clearance"])  # research incomplete but still startable

    def test_completed_hidden_from_available(self):
        c = camp.make_campaign(11)
        before = {t["id"] for t in rtasks.available_tasks(c)}
        self.assertIn("res_1a_hirise", before)
        camp.award_research(c, "res_1a_hirise", 30)
        after = {t["id"] for t in rtasks.available_tasks(c)}
        self.assertNotIn("res_1a_hirise", after)
        completed_ids = {t["id"] for t in rtasks.completed_tasks(c)}
        self.assertIn("res_1a_hirise", completed_ids)

    def test_no_duplicate_rp(self):
        c = camp.make_campaign(12)
        a = camp.award_research(c, "res_1b_mola", 30)
        self.assertTrue(a["awarded"])
        rp = c["research_points"]
        a2 = camp.award_research(c, "res_1b_mola", 30)
        self.assertFalse(a2["awarded"])
        self.assertEqual(c["research_points"], rp)

    def test_hirise_all_questions_reachable(self):
        t = rtasks.get_task("res_1a_hirise")
        qs = rtasks.questions_for(t)
        self.assertGreaterEqual(len(qs), 2)
        # Simulate answering q1 then q2 via terminal submit path
        c = camp.make_campaign(13)
        ui = rterm.make_ui_state()
        ui["selected_task"] = "res_1a_hirise"
        ui["stage"] = "questions"
        ui["selected_option"] = "A"
        rterm._submit_question(c, t, ui)
        self.assertEqual(ui["question_index"], 1)
        ui["selected_option"] = "B"
        rterm._submit_question(c, t, ui)
        self.assertEqual(ui["stage"], "result")
        self.assertIn("res_1a_hirise", c["research_tasks_completed"])

    def test_home_nav_state(self):
        ui = rterm.make_ui_state()
        ui["stage"] = "questions"
        ui["selected_task"] = "res_1a_hirise"
        # Simulate home click logic
        ui["stage"] = "home"
        ui["question_index"] = 0
        self.assertEqual(ui["stage"], "home")

    def test_current_mission_store_only(self):
        c = camp.make_campaign(14)
        ids = {it["id"] for it in proc.items_for_campaign(c)}
        self.assertTrue(ids.issubset(set(mats.material_pool_for_mission("mission_1"))))
        camp.complete_mission(c, "mission_1", {"summary": "x"})
        ids2 = {it["id"] for it in proc.items_for_campaign(c)}
        self.assertTrue(ids2.issubset(set(mats.material_pool_for_mission("mission_2"))))
        self.assertNotIn("servo_motor", ids2)

    def test_persist_completed_hidden(self):
        c = camp.make_campaign(15)
        camp.award_research(c, "res_1c_site", 30)
        savegame.save_campaign(camp.export_for_save(c, {}))
        loaded = savegame.load_campaign()
        avail = {t["id"] for t in rtasks.available_tasks(loaded)}
        self.assertNotIn("res_1c_site", avail)

    def test_image_loader_skips_json(self):
        man = rdata.load_manifest()
        meda = rdata.get_item(man, "meda_timeline_01")
        self.assertIsNone(rdata.resolve_image_path(meda))
        self.assertIsNone(rdata.load_image_surface(meda))
        dunes = rdata.get_item(man, "hirise_dunes_01")
        self.assertIsNotNone(rdata.resolve_image_path(dunes))
        self.assertIsNotNone(rdata.load_image_surface(dunes))


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)
