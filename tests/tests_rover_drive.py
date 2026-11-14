"""Challenge 3 rover drive — physics, terrain, rescue, regression hooks."""

from __future__ import annotations

import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["MARS_MISSION_SAVE_DIR"] = tempfile.mkdtemp(prefix="marsmission_rover_")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from systems import challenges_ch3 as ch3mod
from systems import rover_navigation as rover_nav
from systems import rover_physics as rover_phys
from systems import rover_terrain as rover_terrain


class FakeKeys(dict):
    def __getitem__(self, key):
        return dict.get(self, key, False)


class RoverDriveTests(unittest.TestCase):
    def test_accelerate_and_coast(self):
        ch3 = ch3mod.make_state()
        ch3["route"] = "direct"
        ch3mod.apply_route(ch3)
        ch3["repair_ok"] = True
        keys = FakeKeys({pygame.K_w: True})
        for _ in range(30):
            ch3mod.update_drive(ch3, 1 / 60, keys)
        self.assertGreater(ch3["speed"], 40)
        keys = FakeKeys()
        spd = ch3["speed"]
        for _ in range(45):
            ch3mod.update_drive(ch3, 1 / 60, keys)
        self.assertLess(ch3["speed"], spd)
        self.assertGreaterEqual(ch3["speed"], 0)

    def test_frame_rate_independence_rough(self):
        def run(dt, steps):
            c = ch3mod.make_state()
            c["route"] = "safe"
            ch3mod.apply_route(c)
            c["repair_ok"] = True
            keys = FakeKeys({pygame.K_w: True})
            for _ in range(steps):
                ch3mod.update_drive(c, dt, keys)
            return c["rover_x"], c["speed"]

        x60, s60 = run(1 / 60, 60)
        x30, s30 = run(1 / 30, 30)
        self.assertAlmostEqual(s60, s30, delta=25)
        self.assertAlmostEqual(x60, x30, delta=80)

    def test_steering_smooth(self):
        ch3 = ch3mod.make_state()
        ch3["route"] = "direct"
        ch3mod.apply_route(ch3)
        ch3["repair_ok"] = True
        ch3["speed"] = 120
        h0 = ch3["heading"]
        keys = FakeKeys({pygame.K_w: True, pygame.K_d: True})
        ch3mod.update_drive(ch3, 1 / 60, keys)
        self.assertNotEqual(ch3["heading"], h0)
        # No runaway spin in one frame
        delta = abs((ch3["heading"] - h0 + 180) % 360 - 180)
        self.assertLess(delta, 10)

    def test_terrain_affects_grip(self):
        firm = rover_terrain.sample(200, 200)
        sand = rover_terrain.sample(1200, 1200)
        self.assertEqual(firm["id"], "firm")
        self.assertEqual(sand["id"], "sand")
        self.assertLess(sand["grip"], firm["grip"])

    def test_collision_no_tunnel(self):
        ch3 = ch3mod.make_state()
        ch3["route"] = "shortcut"
        ch3mod.apply_route(ch3)
        ch3["repair_ok"] = True
        # Place against a known rock and drive into it
        rock = ch3["rocks"][0]
        ch3["rover_x"] = rock.centerx - 80
        ch3["rover_y"] = rock.centery
        ch3["heading"] = 0.0
        ch3["speed"] = 200
        keys = FakeKeys({pygame.K_w: True})
        for _ in range(40):
            ch3mod.update_drive(ch3, 1 / 60, keys)
        # Should not be deep inside rock
        r = ch3mod.rover_rect(ch3)
        deep = sum(1 for rock in ch3["rocks"] if rock.contains(r))
        self.assertEqual(deep, 0)

    def test_both_routes_apply(self):
        for key in ("safe", "direct", "shortcut"):
            ch3 = ch3mod.make_state()
            ch3["route"] = key
            ch3mod.apply_route(ch3)
            self.assertGreater(len(ch3["waypoints"]), 2)
            self.assertEqual(ch3["target_x"], ch3["waypoints"][-1]["x"])
            self.assertTrue(ch3["rocks"])

    def test_rescue_radius(self):
        ch3 = ch3mod.make_state()
        ch3["route"] = "direct"
        ch3mod.apply_route(ch3)
        ch3["rover_x"] = ch3["target_x"] - 400
        ch3["rover_y"] = ch3["target_y"]
        self.assertFalse(ch3mod.try_rescue(ch3))
        self.assertIn("closer", ch3["rescue_hint"].lower())
        ch3["rover_x"] = ch3["target_x"]
        ch3["rover_y"] = ch3["target_y"]
        self.assertTrue(ch3mod.try_rescue(ch3))
        self.assertTrue(ch3["rescued"])
        self.assertEqual(ch3["speed"], 0.0)

    def test_scan_and_repair_intact(self):
        self.assertEqual(ch3mod.CORRECT_CELL, "B2")
        self.assertEqual(ch3mod.WRONG_PENALTY, 5)
        self.assertEqual(ch3mod.TIME_LIMIT, 120)
        self.assertEqual(ch3mod.REPAIR_SLOTS["motor"]["needs"], "servo_motor")

    def test_draw_drive_smoke(self):
        ch3 = ch3mod.make_state()
        ch3["route"] = "safe"
        ch3mod.apply_route(ch3)
        fonts = {
            "title": pygame.font.SysFont("segoeui", 28),
            "body": pygame.font.SysFont("segoeui", 18),
            "small": pygame.font.SysFont("segoeui", 14),
            "button": pygame.font.SysFont("segoeui", 16),
        }
        surf = pygame.Surface((1280, 720))
        ch3mod.draw_drive(surf, ch3, fonts)
        ch3mod.draw_route(surf, fonts, (0, 0), ch3)

    def test_physics_config_centralized(self):
        self.assertIn("max_forward", rover_phys.CONFIG)
        self.assertIn("lateral_grip", rover_phys.CONFIG)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)
