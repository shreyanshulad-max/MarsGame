"""Mission 3 Rover Repair workbench — supplies sync and installation tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["MARS_MISSION_SAVE_DIR"] = tempfile.mkdtemp(prefix="marsmission_wb_m3_")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["MARS_DEBUG_WORKBENCH"] = "0"

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from systems import challenges_ch3 as ch3mod
from systems import inventory as inv_sys
from systems import materials as mats
from systems import procurement as proc
from systems import campaign as camp
from systems import workbench as wb
from systems import savegame

savegame.configure_paths(Path(os.environ["MARS_MISSION_SAVE_DIR"]))


def _stock_with_m3(inv, **overrides):
    base = {
        "servo_motor": 1,
        "battery_cell": 1,
        "lubricant": 1,
        "metal_bracket": 1,
    }
    base.update(overrides)
    for mid, qty in base.items():
        inv["stock"][mid]["qty"] = qty
        inv["stock"][mid]["reserved"] = 0


class WorkbenchM3Tests(unittest.TestCase):
    def test_required_materials_always_listed(self):
        inv = inv_sys.make_inventory()
        # Stock flooded with Mission 1/2 materials that previously clipped the panel
        for mid, qty in (
            ("copper_wire", 2),
            ("signal_amplifier", 1),
            ("spare_fuse", 1),
            ("insulated_cable", 2),
        ):
            inv["stock"][mid]["qty"] = qty
        _stock_with_m3(inv)
        rows = wb.build_supply_rows(inv, "ch3", {})
        req_ids = [r["id"] for r in rows["required"]]
        self.assertEqual(
            req_ids,
            ["servo_motor", "battery_cell", "lubricant", "metal_bracket"],
        )
        other_ids = [r["id"] for r in rows["other"]]
        self.assertIn("copper_wire", other_ids)
        self.assertNotIn("servo_motor", other_ids)

    def test_zero_qty_required_still_shown(self):
        inv = inv_sys.make_inventory()
        rows = wb.build_supply_rows(inv, "ch3", {})
        by_id = {r["id"]: r for r in rows["required"]}
        self.assertEqual(by_id["servo_motor"]["status"], "missing")
        self.assertIn("0 available / 1 required", by_id["servo_motor"]["status_text"])

    def test_installed_status(self):
        inv = inv_sys.make_inventory()
        _stock_with_m3(inv)
        ch3 = ch3mod.make_state()
        inv["selected"] = "battery_cell"
        ok, msg = ch3mod.place_repair(ch3, "battery", inv)
        self.assertTrue(ok, msg)
        rows = wb.build_supply_rows(inv, "ch3", ch3["repair"])
        batt = next(r for r in rows["required"] if r["id"] == "battery_cell")
        self.assertEqual(batt["status"], "installed")
        self.assertEqual(batt["status_text"], "INSTALLED")
        self.assertEqual(mats.available(inv["stock"], "battery_cell"), 0)
        self.assertEqual(inv["stock"]["battery_cell"]["qty"], 1)

    def test_reject_incompatible_without_consume(self):
        inv = inv_sys.make_inventory()
        _stock_with_m3(inv)
        inv["stock"]["copper_wire"]["qty"] = 2
        ch3 = ch3mod.make_state()
        inv["selected"] = "copper_wire"
        ok, msg = ch3mod.place_repair(ch3, "motor", inv)
        self.assertFalse(ok)
        self.assertEqual(inv["stock"]["copper_wire"]["qty"], 2)
        self.assertIsNone(ch3["repair"]["motor"])
        self.assertIn("drive motor", msg.lower())

    def test_undo_returns_once(self):
        inv = inv_sys.make_inventory()
        _stock_with_m3(inv)
        ch3 = ch3mod.make_state()
        inv["selected"] = "servo_motor"
        ch3mod.place_repair(ch3, "motor", inv)
        self.assertEqual(mats.available(inv["stock"], "servo_motor"), 0)
        ch3mod.clear_repair(ch3, "motor", inv)
        self.assertEqual(mats.available(inv["stock"], "servo_motor"), 1)
        self.assertEqual(inv["stock"]["servo_motor"]["qty"], 1)
        # Second undo does nothing / no duplication
        ch3mod.clear_repair(ch3, "motor", inv)
        self.assertEqual(inv["stock"]["servo_motor"]["qty"], 1)

    def test_reset_no_duplication(self):
        inv = inv_sys.make_inventory()
        _stock_with_m3(inv)
        ch3 = ch3mod.make_state()
        for mid, slot in (
            ("servo_motor", "motor"),
            ("battery_cell", "battery"),
            ("lubricant", "wheel"),
            ("metal_bracket", "bracket"),
        ):
            inv["selected"] = mid
            ch3mod.place_repair(ch3, slot, inv)
        wb.clear_all(inv, ch3["repair"])
        for mid in ("servo_motor", "battery_cell", "lubricant", "metal_bracket"):
            self.assertEqual(inv["stock"][mid]["qty"], 1)
            self.assertEqual(inv["stock"][mid]["reserved"], 0)
            self.assertEqual(mats.available(inv["stock"], mid), 1)

    def test_procurement_appears_in_rows(self):
        c = camp.make_campaign(77)
        # Jump to mission 3 store
        camp.complete_mission(c, "mission_1", {"summary": "t"})
        camp.complete_mission(c, "mission_2", {"summary": "t"})
        inv = inv_sys.make_inventory()
        c["research_points"] = 200
        ok, msg = proc.purchase(c, inv, "lubricant", 1)
        self.assertTrue(ok, msg)
        rows = wb.build_supply_rows(inv, "ch3", {})
        lube = next(r for r in rows["required"] if r["id"] == "lubricant")
        self.assertEqual(lube["status"], "available")
        self.assertGreaterEqual(lube["available"], 1)

    def test_collection_updates_rows(self):
        inv = inv_sys.make_inventory()
        inv_sys.add_item(
            inv,
            {"id": "cache_test_servo", "material": "servo_motor", "qty": 1, "name": "Servo"},
        )
        rows = wb.build_supply_rows(inv, "ch3", {})
        servo = next(r for r in rows["required"] if r["id"] == "servo_motor")
        self.assertEqual(servo["available"], 1)

    def test_progress_count_validated_slots(self):
        inv = inv_sys.make_inventory()
        _stock_with_m3(inv)
        ch3 = ch3mod.make_state()
        inv["selected"] = "servo_motor"
        ch3mod.place_repair(ch3, "motor", inv)
        filled = sum(
            1 for key, meta in ch3mod.REPAIR_SLOTS.items() if ch3["repair"].get(key) == meta["needs"]
        )
        self.assertEqual(filled, 1)

    def test_ch1_required_not_broken(self):
        inv = inv_sys.make_inventory()
        inv["stock"]["servo_motor"]["qty"] = 1
        inv["stock"]["copper_wire"]["qty"] = 1
        inv["stock"]["signal_amplifier"]["qty"] = 1
        inv["stock"]["spare_fuse"]["qty"] = 1
        rows = wb.build_supply_rows(inv, "ch1", {"coil": None, "amp": None, "fuse": None})
        req_ids = [r["id"] for r in rows["required"]]
        self.assertEqual(req_ids, ["copper_wire", "signal_amplifier", "spare_fuse"])
        self.assertIn("servo_motor", [r["id"] for r in rows["other"]])

    def test_draw_panel_shows_all_required(self):
        inv = inv_sys.make_inventory()
        for mid, qty in (
            ("copper_wire", 2),
            ("signal_amplifier", 1),
            ("spare_fuse", 1),
            ("insulated_cable", 2),
            ("battery_cell", 1),
            ("servo_motor", 1),
            ("lubricant", 1),
            ("metal_bracket", 1),
        ):
            inv["stock"][mid]["qty"] = qty
        fonts = {
            "title": pygame.font.SysFont("segoeui", 28),
            "body": pygame.font.SysFont("segoeui", 18),
            "small": pygame.font.SysFont("segoeui", 14),
        }
        surface = pygame.Surface((1280, 720))
        rects = wb.draw_supply_panel(
            surface, fonts, inv, (0, 0), "ch3",
            pygame.Rect(980, 130, 250, 420),
            slots_state={},
        )
        for mid in ("servo_motor", "battery_cell", "lubricant", "metal_bracket"):
            self.assertIn(mid, rects, f"{mid} missing from hit targets (clipped?)")
        # Unrelated mission materials are not primary hit targets unless Other expanded
        self.assertNotIn("copper_wire", rects)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)
