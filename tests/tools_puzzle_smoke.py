"""Smoke tests for materials + puzzle redesign."""

from __future__ import annotations

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
from systems import inventory as inv_sys
from systems import journal as journal_mod
from systems import materials as mats

fonts = {
    "title": pygame.font.SysFont("segoeui", 28, bold=True),
    "body": pygame.font.SysFont("segoeui", 22),
    "small": pygame.font.SysFont("segoeui", 18),
    "button": pygame.font.SysFont("segoeui", 22, bold=True),
    "button_small": pygame.font.SysFont("segoeui", 18, bold=True),
}
surf = pygame.display.get_surface()
mouse = (640, 360)
ok = fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name} {detail}")


print("=== Materials / inventory ===")
inv = inv_sys.make_inventory()
for p in mats.WORLD_PICKUPS:
    item = {"id": p["uid"], "material": p["material"], "qty": p["qty"], "name": p["material"]}
    inv_sys.add_item(inv, item)
check("copper >=3", inv["stock"]["copper_wire"]["qty"] >= 3)
check("amp 1", inv["stock"]["signal_amplifier"]["qty"] == 1)
check("fuse >=2", inv["stock"]["spare_fuse"]["qty"] >= 2)
check("cable 2", inv["stock"]["insulated_cable"]["qty"] == 2)
check("battery 1", inv["stock"]["battery_cell"]["qty"] == 1)
check("servo 1", inv["stock"]["servo_motor"]["qty"] == 1)
check("no dupe collect", not inv_sys.add_item(inv, {"id": "mat_amp_1", "material": "signal_amplifier", "qty": 1}))

print("=== Journal clues ===")
j = journal_mod.make_journal()
check("add clue", journal_mod.add_clue(j, "ch1_symptom_weak"))
check("no dupe clue", not journal_mod.add_clue(j, "ch1_symptom_weak"))

print("=== CH1 assembly faults ===")
ch1 = ch1mod.make_state()
ch1["phase"] = "assemble"
# incompatible placement rejected without consuming
inv["selected"] = "spare_fuse"
fuse_before = inv["stock"]["spare_fuse"]["qty"]
msg = ch1mod.place_in_slot(ch1, "coil", inv)
check("wrong part rejected", ch1["assembly"]["coil"] is None and inv["stock"]["spare_fuse"]["qty"] == fuse_before, msg)
check("release on clear", mats.available(inv["stock"], "spare_fuse") >= 1)

inv["selected"] = "copper_wire"
ch1mod.place_in_slot(ch1, "coil", inv)
inv["selected"] = "signal_amplifier"
ch1mod.place_in_slot(ch1, "amp", inv)
inv["selected"] = "spare_fuse"
ch1mod.place_in_slot(ch1, "fuse", inv)
ch1["cable_ok"] = False
ch1mod.test_assembly(ch1, inv)
check("fail without cable", not ch1["assembly_ok"])
ch1["cable_ok"] = True
ch1mod.test_assembly(ch1, inv)
check("pass assembly", ch1["assembly_ok"])
check("materials committed", inv["stock"]["copper_wire"]["qty"] == 2)  # 3-1

# Align packets still required
ch1["phase"] = "align"
ch1["antenna_angle"] = 20
ch1["interference"] = 0
ch1["interference_cd"] = 99
for _ in range(5):
    ch1mod.update(ch1, 1 / 60, False, True)
check("no instant win", not ch1["connection_restored"])
for _ in range(220):
    ch1["interference"] = 0
    ch1["interference_cd"] = 99
    ch1mod.update(ch1, 1 / 60, False, True)
    if ch1["connection_restored"]:
        break
check("packets restore", ch1["connection_restored"] and ch1["packets"] >= 3)

print("=== CH2 circuit ===")
ch2 = ch2mod.make_state()
inv2 = inv_sys.make_inventory()
for p in mats.WORLD_PICKUPS:
    inv_sys.add_item(inv2, {"id": p["uid"], "material": p["material"], "qty": p["qty"]})
ch2mod.test_circuit(ch2, inv2)
check("fail empty circuit", not ch2["circuit_ok"])
# Install fuse + all required links
ch2mod.install_fuse(ch2, inv2)
for a, b in ch2mod.REQUIRED_LINKS:
    ch2["links"].append((a, b))
ch2mod.test_circuit(ch2, inv2)
check("pass circuit", ch2["circuit_ok"] and ch2["wires_done"])

# reversed polarity detection
ch2b = ch2mod.make_state()
ch2b["fuse_installed"] = True
ch2b["links"] = [("solar.out_p", "controller.in_n")]
faults = ch2mod.circuit_faults(ch2b)
check("detect reverse", any("REVERSED" in f for f in faults), str(faults))

ch2["life"] = 30
ch2["food"] = 30
ch2["comms"] = 10
ch2["confirmed_alloc"] = False
ch2mod.update(ch2, 0.1, True)
check("need confirm", not ch2["completed"])
ch2["confirmed_alloc"] = True
ch2mod.update(ch2, 0.1, True)
check("complete after confirm", ch2["completed"])
bon = ch2mod.allocation_bonuses({"life": 40, "food": 30, "comms": 20})
check("extra life 10", bon["extra_life"] == 10)
check("extra comms 10", bon["extra_comms"] == 10)

print("=== CH3 repair / route ===")
ch3 = ch3mod.make_state()
inv3 = inv_sys.make_inventory()
for p in mats.WORLD_PICKUPS:
    inv_sys.add_item(inv3, {"id": p["uid"], "material": p["material"], "qty": p["qty"]})
ch3mod.test_repair(ch3, inv3)
check("fail empty repair", not ch3["repair_ok"])
for slot, meta in ch3mod.REPAIR_SLOTS.items():
    inv3["selected"] = meta["needs"]
    ch3mod.place_repair(ch3, slot, inv3)
ch3mod.test_repair(ch3, inv3)
check("repair pass", ch3["repair_ok"])
ch3["route"] = "safe"
ch3mod.apply_route(ch3)
check("route traction", ch3["traction_mod"] > 1.0)
ch3["scan_clarity"] = 0.5
ui = ch3mod.draw_scan(surf, fonts, mouse, ch3)
check("scan ui", "cells" in ui and len(ui["cells"]) == 9)
check("B2 strong", ch3mod.SIGNALS["B2"] == "Strong")
check("wrong penalty 5", ch3mod.WRONG_PENALTY == 5)

print("=== main import ===")
sys.path.insert(0, r"C:\MarsMission")
import main as game

check("ch1 screens", hasattr(game, "SCREEN_CH1_DIAG") and hasattr(game, "SCREEN_CH1_ASSEMBLE"))
check("ch3 screens", hasattr(game, "SCREEN_CH3_REPAIR") and hasattr(game, "SCREEN_CH3_ROUTE"))
st = game.make_challenge1_state()
check("ch1 diagnose start", st["phase"] == "diagnose")

print()
print(f"RESULT: {ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
