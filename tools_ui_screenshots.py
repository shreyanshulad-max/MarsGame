"""Render redesigned UI panels to PNG for visual review (no gameplay changes)."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((1280, 720))

from systems import campaign as camp
from systems import campaign_ui as camp_ui
from systems import challenge_ui as ui
from systems import colony as colony_sys
from systems import guidance as guide
from systems import hud_explore
from systems import inventory as inv_sys
from systems import minimap as map_sys
from systems import notify as notify_sys
from systems import player as player_sys
from systems import procurement as proc
from systems import research_terminal as research_term
from systems import camera as cam_sys

OUT = os.path.join(os.path.dirname(__file__), "ui_review")
os.makedirs(OUT, exist_ok=True)

fonts = {
    "title": pygame.font.SysFont("segoeui", 26, bold=True),
    "body": pygame.font.SysFont("segoeui", 15),
    "small": pygame.font.SysFont("segoeui", 12),
    "button": pygame.font.SysFont("segoeui", 15, bold=True),
    "button_small": pygame.font.SysFont("segoeui", 12, bold=True),
}


def save(surface, name):
    path = os.path.join(OUT, name)
    pygame.image.save(surface, path)
    print("wrote", path)


def backdrop(surface):
    surface.fill((90, 55, 40))
    for i in range(0, 1280, 40):
        pygame.draw.line(surface, (70, 42, 30), (i, 0), (i, 720), 1)


# --- Explore HUD ---
screen = pygame.Surface((1280, 720))
backdrop(screen)
colony = colony_sys.make_colony("ch1", "ch2", "ch3", "research", "shop")
astro = player_sys.make_astronaut(colony["spawn"])
cam = cam_sys.make_camera(astro, 1280, 720)
discovery = map_sys.make_discovery(colony["spawn"])
inv = inv_sys.make_inventory()
c = camp.make_campaign(7)
obj = guide.resolve_objective(c, inv, colony, discovery)
g = guide.make_guidance()
guide.update(g, 0.5, astro, obj, colony["colliders"])
guide.draw_world_arrow(screen, fonts, g, astro, cam)
hud_explore.draw_explore_hud(
    screen, fonts, astro, colony, cam,
    "OFFLINE", "LOW", "AT RISK", "MISSING", 0,
    "Habitat", guide.objective_label(obj), 0,
    prompt="E - Open Research Terminal",
    discovery=discovery, inventory=inv, guide_obj=obj,
)
n = notify_sys.make_notifier()
notify_sys.push(n, "Collected: Copper Wire ×1", "success")
notify_sys.draw(screen, fonts, n)
save(screen, "01_explore_hud.png")

# --- Inventory ---
backdrop(screen)
inv["open"] = True
from systems import materials as mats
mats.add_material(inv["stock"], "copper_wire", 2)
inv["selected"] = "copper_wire"
inv["detail_mid"] = "copper_wire"
inv_sys.draw_inventory(screen, fonts, inv, (400, 200))
save(screen, "02_inventory.png")

# --- Procurement ---
backdrop(screen)
c["research_points"] = 80
shop = {"selected": "copper_wire"}
proc.draw_shop(screen, fonts, (900, 400), c, inv, ui_state=shop)
save(screen, "03_procurement.png")

# --- Research ---
backdrop(screen)
rui = research_term.make_ui_state()
tasks = __import__("systems.research_tasks", fromlist=["tasks_for_tier"]).tasks_for_tier(1)
if tasks:
    rui["selected_task"] = tasks[0]["id"]
research_term.draw(screen, fonts, (600, 300), c, rui)
save(screen, "04_research.png")

# --- Dashboard ---
backdrop(screen)
camp_ui.draw_dashboard(screen, fonts, (200, 200), c, inv)
save(screen, "05_dashboard.png")

# --- Full map ---
backdrop(screen)
map_sys.draw_full_map(
    screen, fonts, astro, colony, colony["world_w"], colony["world_h"], True,
    discovery=discovery, mouse_pos=(100, 100), guide_obj=obj,
)
save(screen, "06_full_map.png")

# --- Challenge frame ---
backdrop(screen)
ui.challenge_frame(screen, fonts, "Communication Blackout", "Radar scan", progress=0.4, time_left=42, hint="Tune frequency and gain")
ui.soft_panel(screen, pygame.Rect(200, 140, 880, 480), 180)
ui.centered(screen, fonts, "Puzzle area (dominant)", (640, 380), ui.C_MUTED, "body")
ui.footer_hint(screen, fonts, "Arrow keys tune · Click contacts · Esc leaves safely")
save(screen, "07_challenge_frame.png")

# --- Pause ---
backdrop(screen)
hud_explore.draw_explore_hud(
    screen, fonts, astro, colony, cam,
    "ONLINE", "ONLINE", "SAFE", "RESCUED", 300,
    "Habitat", "Explore", 3, paused=True, discovery=discovery, guide_obj=obj,
)
save(screen, "08_pause.png")

# --- Title chrome ---
backdrop(screen)
brand = fonts["title"].render("MARS MISSION", True, ui.C_MARS)
screen.blit(brand, brand.get_rect(center=(640, 210)))
sub = fonts["body"].render("Restore · Recharge · Rescue", True, ui.C_TEXT)
screen.blit(sub, sub.get_rect(center=(640, 250)))
btn = pygame.Rect(0, 0, 280, 52)
btn.center = (640, 640)
ui.button(screen, btn, "START MISSION", fonts, (640, 640), accent=True)
save(screen, "09_title.png")

print("Done. Screenshots in", OUT)
