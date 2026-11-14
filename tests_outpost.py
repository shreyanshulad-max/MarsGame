"""Outpost systems + antenna regression companion tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["MARS_MISSION_SAVE_DIR"] = tempfile.mkdtemp(prefix="marsmission_outpost_")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from systems import campaign as camp
from systems import outpost as op
from systems import savegame

savegame.configure_paths(Path(os.environ["MARS_MISSION_SAVE_DIR"]))


class OutpostTests(unittest.TestCase):
    def test_init_and_migrate(self):
        c = camp.make_campaign(seed=1)
        self.assertIn("outpost", c)
        op.ensure_outpost(c)
        for key in ("life_support", "radiation", "power", "food"):
            self.assertIn(key, c["outpost"])

    def test_power_budget_cap(self):
        c = camp.make_campaign(2)
        state = op.ensure_outpost(c)
        ok, msg = op.set_allocation(state, "life_support", 90)
        self.assertFalse(ok)
        ok, _ = op.set_allocation(state, "life_support", 25)
        self.assertTrue(ok)
        ok, _ = op.confirm_allocation(state)
        self.assertTrue(ok)

    def test_life_support_responds(self):
        c = camp.make_campaign(3)
        state = op.ensure_outpost(c)
        op.set_allocation(state, "life_support", 5)
        op.set_allocation(state, "food", 10)
        op.set_allocation(state, "comms", 10)
        op.set_allocation(state, "thermal", 10)
        op.set_allocation(state, "lighting", 5)
        # Force under-min life after confirm
        state["power"]["allocation"]["life_support"] = 5
        state["power"]["confirmed"] = True
        op._recompute(state)
        self.assertTrue(state["life_support"]["warning"])

    def test_greenhouse_needs_power(self):
        c = camp.make_campaign(4)
        state = op.ensure_outpost(c)
        op.confirm_allocation(state)
        state["power"]["allocation"]["food"] = 0
        op._recompute(state)
        op.tick_greenhouse(state, 1.0)
        self.assertEqual(state["food"]["status"], "NEEDS POWER")
        state["power"]["allocation"]["food"] = 15
        # Keep under budget
        state["power"]["allocation"]["lighting"] = 5
        op.confirm_allocation(state)
        op.tick_greenhouse(state, 5.0)
        self.assertIn(state["food"]["status"], ("GROWING", "READY", "NEEDS RESOURCES"))

    def test_shielding_persists(self):
        c = camp.make_campaign(5)
        state = op.ensure_outpost(c)
        op.set_shielding(state, "regolith_sim")
        savegame.save_campaign(camp.export_for_save(c, {}))
        loaded = savegame.load_campaign()
        self.assertEqual(loaded["outpost"]["radiation"]["shielding_config"], "regolith_sim")

    def test_mission_hooks(self):
        c = camp.make_campaign(6)
        camp.complete_mission(c, "mission_1", {"summary": "ok"})
        self.assertTrue(any("Communications" in x for x in c["outpost"]["log"]))


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)
