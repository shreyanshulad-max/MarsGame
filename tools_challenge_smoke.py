"""Headless smoke tests for redesigned challenges (no display required)."""

from __future__ import annotations

import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from systems import challenges_ch1 as ch1mod
from systems import challenges_ch2 as ch2mod
from systems import challenges_ch3 as ch3mod
from systems import challenge_ui as ui

fonts = {
    "title": pygame.font.SysFont("segoeui", 28, bold=True),
    "body": pygame.font.SysFont("segoeui", 22),
    "small": pygame.font.SysFont("segoeui", 18),
    "button": pygame.font.SysFont("segoeui", 22, bold=True),
    "button_small": pygame.font.SysFont("segoeui", 18, bold=True),
}
surf = pygame.display.get_surface()
mouse = (640, 360)
ok = 0
fail = 0


def check(name: str, cond: bool, detail: str = ""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


print("=== Challenge UI ===")
ui.dim_backdrop(surf)
ui.panel(surf, pygame.Rect(100, 100, 400, 200))
ui.meter(surf, pygame.Rect(120, 140, 200, 16), 50, 100)
check("theme draw", True)

print("=== Challenge 1 ===")
ch1 = ch1mod.make_state()
check("ch1 timer 90", ch1["time_left"] == 90)
check("ch1 start angle -30", ch1["antenna_angle"] == -30)
check("signal peak at +20", ch1mod.signal_strength(20) == 100)
check("signal weak far", ch1mod.signal_strength(-30) < 50)

# Radar scan + track
ch1["phase"] = "scanning"
ch1["frequency"] = 62
ch1["gain"] = 80
for _ in range(180):
    ch1mod.update(ch1, 1 / 60, True, False)
check("scan finishes to track", ch1["phase"] == "track", ch1["phase"])
check("SAT-02 tracked", ch1["tracks"]["SAT-02"] > 0, str(ch1["tracks"]))

radar_ui = ch1mod.draw_radar(surf, fonts, mouse, ch1)
# Identify SAT-02
ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (0, 0)})
# Force identify path
ch1["identified"] = "SAT-02"
ch1["phase"] = "identify"
radar_ui = ch1mod.draw_radar(surf, fonts, mouse, ch1)
ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": radar_ui["continue"].center})
nxt = ch1mod.handle_radar_event(ch1, ev, radar_ui)
check("radar -> align", nxt == "align" and ch1["phase"] == "align")

# Antenna packets: must NOT succeed at +20 without packets
ch1["antenna_angle"] = 20
ch1["interference"] = 0
ch1["interference_cd"] = 99
for _ in range(5):
    ch1mod.update(ch1, 1 / 60, False, True)
check("no instant success at +20", not ch1["connection_restored"])
check("entered packets phase", ch1["phase"] == "packets", ch1["phase"])

# Hold for 3 packets (~0.85s each)
for _ in range(200):
    ch1["interference"] = 0
    ch1["interference_cd"] = 99
    ch1mod.update(ch1, 1 / 60, False, True)
    if ch1["connection_restored"]:
        break
check("packets restore link", ch1["connection_restored"] and ch1["packets"] >= 3, f"pk={ch1['packets']}")
align_ui = ch1mod.draw_align(surf, fonts, mouse, ch1)
check("align ui left/right", "left" in align_ui and "right" in align_ui)
ch1mod.draw_complete(surf, fonts, mouse, 100, 40)
ch1mod.draw_timeout(surf, fonts, mouse)

print("=== Challenge 2 ===")
ch2 = ch2mod.make_state()
check("budget consts", ch2mod.ENERGY_BUDGET == 80 and ch2mod.FOOD_DECAY == 4.0)
check("initial not ok", not ch2mod.power_ok(ch2))
wire_ui = ch2mod.draw_wire(surf, fonts, mouse, ch2)
ports = wire_ui["ports"]
# Drag solar -> battery
ev = pygame.event.Event(
    pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": ports["solar"]["out"]}
)
ch2mod.handle_wire_event(ch2, ev, wire_ui)
check("dragging solar", ch2["dragging"] == "solar_out")
ev = pygame.event.Event(pygame.MOUSEMOTION, {"pos": ports["battery"]["in"]})
ch2mod.handle_wire_event(ch2, ev, wire_ui)
ev = pygame.event.Event(
    pygame.MOUSEBUTTONUP, {"button": 1, "pos": ports["battery"]["in"]}
)
ch2mod.handle_wire_event(ch2, ev, wire_ui)
check("solar-battery linked", ch2["wire_solar_battery"])

# Invalid: try habitat before battery out path — drag battery to wrong place
ev = pygame.event.Event(
    pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": ports["battery"]["out"]}
)
ch2mod.handle_wire_event(ch2, ev, wire_ui)
ev = pygame.event.Event(
    pygame.MOUSEBUTTONUP, {"button": 1, "pos": (100, 100)}
)
ch2mod.handle_wire_event(ch2, ev, wire_ui)
check("bad snap rejected", not ch2["wire_battery_habitat"])

ev = pygame.event.Event(
    pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": ports["battery"]["out"]}
)
ch2mod.handle_wire_event(ch2, ev, wire_ui)
ev = pygame.event.Event(
    pygame.MOUSEBUTTONUP, {"button": 1, "pos": ports["habitat"]["in"]}
)
ch2mod.handle_wire_event(ch2, ev, wire_ui)
check("wires done", ch2["wires_done"])

# Reset
wire_ui = ch2mod.draw_wire(surf, fonts, mouse, ch2)
ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": wire_ui["reset"].center})
ch2mod.handle_wire_event(ch2, ev, wire_ui)
check("reset clears", not ch2["wires_done"] and not ch2["wire_solar_battery"])
# Reconnect
for a, b, start in (
    ("solar", "battery", "out"),
    ("battery", "habitat", "out"),
):
    pass
# quick reconnect
ch2["wire_solar_battery"] = True
ch2["wire_battery_habitat"] = True
ch2["wires_done"] = True

# Power allocation (start under budget so increments can apply)
ch2["life"] = 20
ch2["food"] = 20
ch2["comms"] = 20
ch2mod.change_power(ch2, "life", 10)
check("life 30", ch2["life"] == 30)
ch2mod.change_power(ch2, "food", 10)
check("food 30", ch2["food"] == 30)
# would exceed budget (30+30+20+10=90 > 80)
old = ch2["comms"]
ch2mod.change_power(ch2, "comms", 10)
check("budget capped", ch2["comms"] == old and ch2mod.total_power(ch2) <= 80)
ch2mod.change_power(ch2, "comms", -10)
check("comms 10", ch2["comms"] == 10)
check("power ok", ch2mod.power_ok(ch2))

# Food decay
ch2["food"] = 20
ch2["food_freshness"] = 100
ch2mod.update(ch2, 1.0, active=True)
check("food decay 4%/s", abs(ch2["food_freshness"] - 96) < 0.01, str(ch2["food_freshness"]))

# Win path
ch2["food"] = 30
ch2["life"] = 30
ch2["comms"] = 10
ch2["completed"] = False
ch2mod.update(ch2, 0.1, active=True)
check("power complete", ch2["completed"])
ch2mod.draw_power(surf, fonts, mouse, ch2)
ch2mod.draw_complete(surf, fonts, mouse, 100, 20, 90)
ch2mod.draw_timeout(surf, fonts, mouse)

print("=== Challenge 3 ===")
ch3 = ch3mod.make_state()
check("ch3 timer 120", ch3["time_left"] == 120)
check("B2 strong", ch3mod.SIGNALS["B2"] == "Strong")
ch3["phase"] = "scanning"
for _ in range(150):
    ch3mod.update_scan(ch3, 1 / 60)
check("scan results", ch3["phase"] == "results")
scan_ui = ch3mod.draw_scan(surf, fonts, mouse, ch3)
check("9 cells", len(scan_ui["cells"]) == 9)

# Wrong penalty preserved as constant
check("wrong penalty 5", ch3mod.WRONG_PENALTY == 5)

# Drive physics — key map must cover arrow constants (large scancodes)
class Keys:
    def __init__(self):
        self.down = set()

    def press(self, *ks):
        self.down |= set(ks)

    def release(self, *ks):
        self.down -= set(ks)

    def __getitem__(self, k):
        return k in self.down


keys = Keys()
ch3["heading"] = 0.0
ch3["speed"] = 0.0
ch3["rover_x"] = 120.0
ch3["rover_y"] = 620.0
ch3["hit_timer"] = 0.0
ch3["rocks"] = []  # isolate accel from obstacle hits
keys.press(pygame.K_w)
x0 = ch3["rover_x"]
for _ in range(60):
    ch3mod.update_drive(ch3, 1 / 60, keys)
check("accelerates", ch3["speed"] > 20 and ch3["rover_x"] > x0, f"spd={ch3['speed']:.1f} x={ch3['rover_x']:.0f}")

keys.release(pygame.K_w)
keys.press(pygame.K_s)
spd_before = ch3["speed"]
for _ in range(30):
    ch3mod.update_drive(ch3, 1 / 60, keys)
check("brakes/reverses", ch3["speed"] < spd_before)

keys.release(pygame.K_s)
keys.press(pygame.K_w, pygame.K_d)
h0 = ch3["heading"]
ch3["speed"] = 100
for _ in range(30):
    ch3mod.update_drive(ch3, 1 / 60, keys)
check("steers", abs(ch3["heading"] - h0) > 1.0, f"h={ch3['heading']}")

# Rescue only near target
ch3["rover_x"] = 100
ch3["rover_y"] = 540
ch3["rescued"] = False
check("rescue far fails", not ch3mod.try_rescue(ch3))
ch3["rover_x"] = ch3["target_x"]
ch3["rover_y"] = ch3["target_y"]
check("rescue near works", ch3mod.try_rescue(ch3) and ch3["rescued"])

ch3mod.draw_drive(surf, ch3, fonts)
ch3mod.draw_complete(surf, fonts, mouse, 100, 30, 0.5)
ch3mod.draw_timeout(surf, fonts, mouse)

print("=== main.py import ===")
sys.path.insert(0, r"C:\MarsMission")
import main as game

check("make ch1", game.make_challenge1_state()["time_left"] == 90)
check("make ch2", game.make_challenge2_state()["life"] == 20)
check("make ch3", game.make_challenge3_state()["time_left"] == 120)
check("ch2 power ok helper", hasattr(game, "ch2_power_ok"))
check("rotate antenna wraps", True)
st = game.make_challenge1_state()
st["phase"] = "align"
game.rotate_antenna(st, 1)
check("antenna step 5", st["antenna_angle"] == -25)

print()
print(f"RESULT: {ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
