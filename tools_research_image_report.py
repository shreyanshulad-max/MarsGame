"""Diagnose research image references (project-root paths)."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((64, 64))

from systems import research_data as rdata

rows = rdata.diagnose_assets()
ok = fail = 0
print("=== Research image diagnostic ===")
for r in rows:
    status = "OK" if r["exists"] or r["data_type"] in ("timeline", "context_note", "numeric_profile") else "MISSING_IMAGE"
    if status == "OK":
        ok += 1
    else:
        fail += 1
    print(f"  {status:14} {r['task_id']:20} {r['ref']:14} {r['item_id']:24} type={r['data_type']} path={r['path']}")
print(f"RESULT: {ok} ok-or-nonimage, {fail} missing image files")
sys.exit(1 if fail else 0)
