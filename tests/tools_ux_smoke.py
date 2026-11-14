"""UX milestone smoke tests."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from systems import challenges_ch1 as ch1mod
from systems import challenges_ch3 as ch3mod
from systems import inventory as inv_sys
from systems import materials as mats
from systems import minimap as map_sys
from systems import scanner as scanner_sys
from systems import tutorials as tut_sys
from systems import workbench as wb

fonts = {
    "title": pygame.font.SysFont("segoeui", 28, bold=True),
    "body": pygame.font.SysFont("segoeui", 22),
    "small": pygame.font.SysFont("segoeui", 18),
    "button": pygame.font.SysFont("segoeui", 22, bold=True),
    "button_small": pygame.font.SysFont("segoeui", 18, bold=True),
}
surf = pygame.display.get_surface()
ok = fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name} {detail}")


print("=== Workbench / inventory UX ===")
check("guided default", wb.is_guided() is True)
wb.set_guided(False)
check("challenge mode", wb.is_guided() is False)
wb.set_guided(True)

inv = inv_sys.make_inventory()
for p in mats.WORLD_PICKUPS:
    inv_sys.add_item(inv, {"id": p["uid"], "material": p["material"], "qty": p["qty"]})
missing = inv_sys.missing_for_mission(inv, "ch1")
check("ch1 supplies present", len(missing) == 0)

ch1 = ch1mod.make_state()
inv["selected"] = "spare_fuse"
msg = ch1mod.place_in_slot(ch1, "coil", inv)
check("reject incompatible", ch1["assembly"]["coil"] is None and "cannot" in msg.lower() or "coil" in msg.lower() or "requires" in msg.lower(), msg)
check("no consume on reject", inv["stock"]["spare_fuse"]["reserved"] == 0)

inv["selected"] = "copper_wire"
msg = ch1mod.place_in_slot(ch1, "coil", inv)
check("accept compatible", ch1["assembly"]["coil"] == "copper_wire", msg)
check("reserved on install", inv["stock"]["copper_wire"]["reserved"] == 1)
ch1mod.clear_slot(ch1, "coil", inv)
check("undo releases", inv["stock"]["copper_wire"]["reserved"] == 0)

ui = ch1mod.draw_assemble(surf, fonts, (100, 100), ch1, inv)
check("workbench supplies ui", "supplies" in ui and "mode" in ui)

print("=== Tutorials ===")
t = tut_sys.make_tutorials()
tut_sys.trigger(t, "assembly")
check("tip active", t["active"] == "assembly")
tut_sys.dismiss(t)
check("tip dismissed", t["active"] is None and "assembly" in t["seen"])
tut_sys.trigger(t, "assembly")
check("no repeat", t["active"] is None)

print("=== Scanner / discovery ===")
disc = map_sys.make_discovery((1600, 1280))
map_sys.reveal_around(disc, 1600, 1280, 300)
check("fog revealed", len(disc["revealed"]) > 5)
scan = scanner_sys.make_scanner()
colony = {
    "interactables": [
        {"id": "mat_amp_1", "pos": (1650, 1300), "collected": False, "type": "collectible", "material": "signal_amplifier", "name": "Signal Amplifier"},
        {"id": "comm", "pos": (400, 700), "collected": False, "type": "station", "name": "Comm"},
    ]
}
astro = {"x": 1600.0, "y": 1280.0}
scanner_sys.start_scan(scan, astro, colony, disc)
check("scan hits nearby", any(h["id"] == "mat_amp_1" for h in scan["hits"]))
check("far station not hit", not any(h["id"] == "comm" for h in scan["hits"]))
check("scanned marked", "mat_amp_1" in disc["scanned_ids"])

print("=== CH3 scan UX ===")
ch3 = ch3mod.make_state()
ch3["phase"] = "results"
ch3["scanned_cells"]["A1"] = ch3mod._sector_telemetry("A1", 0.5)
ch3["selected_cell"] = "A1"
ui3 = ch3mod.draw_scan(surf, fonts, (400, 200), ch3)
check("grid cells 9", len(ui3["cells"]) == 9)
check("B2 strong", ch3mod.SIGNALS["B2"] == "Strong")
check("penalty const 5", ch3mod.WRONG_PENALTY == 5)

print("=== Map draw ===")
# minimal colony stub for map
class R(pygame.Rect):
    pass

col = {
    "zones": [{"id": "habitat", "name": "Central Habitat", "rect": pygame.Rect(1200, 850, 800, 550), "tint": (210, 120, 70)}],
    "stations": [{"id": "comm", "name": "Comm", "pos": (420, 720), "marker": (90, 200, 255)}],
    "collectibles": [],
    "world_w": 3200,
    "world_h": 2200,
}
mui = map_sys.draw_full_map(surf, fonts, astro, col, 3200, 2200, True, discovery=disc, mouse_pos=(640, 360))
check("map controls", mui["zoom_in"].width > 0 and mui["inner"].width > 0)

print("=== main import ===")
sys.path.insert(0, r"C:\MarsMission")
import main as game
check("imports", hasattr(game, "SCREEN_CH1_ASSEMBLE"))

print()
print(f"RESULT: {ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
