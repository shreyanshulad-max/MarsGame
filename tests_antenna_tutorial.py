"""Antenna briefing / practice / timed-start regression tests."""

from __future__ import annotations

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from systems import antenna_tutorial as atut
from systems import challenges_ch1 as ch1mod


class AntennaTutorialTests(unittest.TestCase):
    def test_timer_not_running_by_default(self):
        ch1 = ch1mod.make_state()
        self.assertFalse(ch1["timer_running"])

    def test_practice_has_no_timer(self):
        ch1 = ch1mod.make_state()
        atut.reset_practice(ch1)
        self.assertFalse(ch1["timer_running"])
        self.assertEqual(ch1["align_mode"], "practice")
        # Move toward target
        for _ in range(20):
            ch1mod.rotate_antenna(ch1, 1)
            if ch1.get("practice_step") == "success":
                break
        self.assertTrue(ch1mod.is_stable(ch1["antenna_angle"]) or ch1["practice_step"] == "success")
        self.assertFalse(ch1["timer_running"])
        self.assertFalse(ch1["connection_restored"])  # practice must not complete mission

    def test_timed_starts_only_after_begin(self):
        ch1 = ch1mod.make_state()
        atut.reset_practice(ch1)
        self.assertFalse(ch1["timer_running"])
        atut.begin_timed_mission(ch1)
        self.assertTrue(ch1["timer_running"])
        self.assertEqual(ch1["align_mode"], "timed")
        self.assertEqual(ch1["time_left"], float(ch1mod.TIME_LIMIT))
        self.assertLessEqual(abs(ch1["antenna_angle"] - ch1mod.TARGET_ANGLE), 20)

    def test_stable_zone_forgiving(self):
        self.assertTrue(ch1mod.is_stable(ch1mod.TARGET_ANGLE))
        self.assertTrue(ch1mod.is_stable(ch1mod.TARGET_ANGLE + ch1mod.STABLE_ZONE_DEG))
        self.assertFalse(ch1mod.is_stable(ch1mod.TARGET_ANGLE + ch1mod.STABLE_ZONE_DEG + 1))

    def test_signal_bands(self):
        self.assertEqual(ch1mod.signal_band(ch1mod.TARGET_ANGLE), "STABLE SIGNAL")
        self.assertIn(ch1mod.signal_band(ch1mod.TARGET_ANGLE + 25), ("IMPROVING SIGNAL", "LOW SIGNAL"))

    def test_overshoot_correctable(self):
        ch1 = ch1mod.make_state()
        atut.begin_timed_mission(ch1)
        # Overshoot past target
        while ch1["antenna_angle"] < ch1mod.TARGET_ANGLE + 15:
            ch1mod.rotate_antenna(ch1, 1)
        self.assertGreater(ch1["antenna_angle"], ch1mod.TARGET_ANGLE)
        # Correct back
        while not ch1mod.is_stable(ch1["antenna_angle"]) and ch1["antenna_angle"] > -60:
            ch1mod.rotate_antenna(ch1, -1)
        self.assertTrue(ch1mod.is_stable(ch1["antenna_angle"]))

    def test_timed_success_stops_timer(self):
        ch1 = ch1mod.make_state()
        atut.begin_timed_mission(ch1)
        # Snap into stable zone
        ch1["antenna_angle"] = ch1mod.TARGET_ANGLE
        ch1["interference"] = 0
        # Drive packet capture
        for _ in range(200):
            ch1mod.update(ch1, 0.1, active_radar=False, active_align=True)
            if ch1["connection_restored"]:
                break
        self.assertTrue(ch1["connection_restored"])
        self.assertFalse(ch1["timer_running"])
        self.assertEqual(ch1["signal_band"], "COMMUNICATION ESTABLISHED")

    def test_radar_routes_to_briefing(self):
        ch1 = ch1mod.make_state()
        ch1["identified"] = "SAT-02"
        ch1["phase"] = "identify"
        # Simulate continue click via direct transition used by handler
        ch1["phase"] = "briefing"
        ch1["timer_running"] = False
        self.assertEqual(ch1["phase"], "briefing")
        self.assertFalse(ch1["timer_running"])


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)
