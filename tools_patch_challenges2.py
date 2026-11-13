"""Replace challenge draw/update functions with redesigned module wrappers."""

from pathlib import Path
import re

path = Path(r"C:\MarsMission\main.py")
text = path.read_text(encoding="utf-8")


def replace_func(name: str, new_body: str):
    global text
    pattern = rf"(def {name}\(.*?\):\n)([\s\S]*?)(?=\n\ndef |\n\n# =====|\n\nif __name__)"
    m = re.search(pattern, text)
    if not m:
        # try until next def at column 0
        pattern2 = rf"def {name}\(.*?\):\n[\s\S]*?(?=\ndef )"
        m2 = re.search(pattern2, text)
        if not m2:
            raise SystemExit(f"FUNC NOT FOUND {name}")
        text = text[: m2.start()] + new_body.strip() + "\n\n" + text[m2.end() :]
        print("OK-re", name)
        return
    text = text[: m.start()] + new_body.strip() + "\n\n" + text[m.end() :]
    print("OK", name)


wrappers = {
    "draw_radar_screen": '''def draw_radar_screen(surface, fonts, mouse_pos, ch1):
    """Interactive radar console for Challenge 1."""
    return ch1mod.draw_radar(surface, fonts, mouse_pos, ch1)
''',
    "draw_alignment_screen": '''def draw_alignment_screen(surface, fonts, mouse_pos, ch1):
    """Antenna calibration with packet acquisition."""
    return ch1mod.draw_align(surface, fonts, mouse_pos, ch1)
''',
    "draw_complete_panel": '''def draw_complete_panel(surface, fonts, mouse_pos, score, time_left):
    return ch1mod.draw_complete(surface, fonts, mouse_pos, score, time_left)
''',
    "draw_timeout_panel": '''def draw_timeout_panel(surface, fonts, mouse_pos):
    return ch1mod.draw_timeout(surface, fonts, mouse_pos)
''',
    "draw_ch2_intro": '''def draw_ch2_intro(surface, fonts, mouse_pos):
    return ch2mod.draw_intro(surface, fonts, mouse_pos)
''',
    "draw_ch2_wire_screen": '''def draw_ch2_wire_screen(surface, fonts, mouse_pos, ch2):
    return ch2mod.draw_wire(surface, fonts, mouse_pos, ch2)
''',
    "draw_ch2_power_screen": '''def draw_ch2_power_screen(surface, fonts, mouse_pos, ch2):
    return ch2mod.draw_power(surface, fonts, mouse_pos, ch2)
''',
    "draw_ch2_complete_panel": '''def draw_ch2_complete_panel(surface, fonts, mouse_pos, score, time_left, freshness):
    return ch2mod.draw_complete(surface, fonts, mouse_pos, score, time_left, freshness)
''',
    "draw_ch2_timeout_panel": '''def draw_ch2_timeout_panel(surface, fonts, mouse_pos):
    return ch2mod.draw_timeout(surface, fonts, mouse_pos)
''',
    "make_challenge3_state": '''def make_challenge3_state():
    """Fresh Challenge 3 state (scan + heading-based rover)."""
    return ch3mod.make_state()
''',
    "draw_ch3_intro": '''def draw_ch3_intro(surface, fonts, mouse_pos):
    return ch3mod.draw_intro(surface, fonts, mouse_pos)
''',
    "draw_ch3_scan_screen": '''def draw_ch3_scan_screen(surface, fonts, mouse_pos, ch3):
    return ch3mod.draw_scan(surface, fonts, mouse_pos, ch3)
''',
    "draw_ch3_drive_world": '''def draw_ch3_drive_world(surface, ch3, fonts):
    ch3mod.draw_drive(surface, ch3, fonts)
''',
    "update_ch3_drive": '''def update_ch3_drive(ch3, dt, keys):
    ch3mod.update_drive(ch3, dt, keys)
''',
    "try_ch3_rescue": '''def try_ch3_rescue(ch3):
    return ch3mod.try_rescue(ch3)
''',
    "draw_ch3_complete_panel": '''def draw_ch3_complete_panel(surface, fonts, mouse_pos, score, time_left, storm):
    return ch3mod.draw_complete(surface, fonts, mouse_pos, score, time_left, storm)
''',
    "draw_ch3_timeout_panel": '''def draw_ch3_timeout_panel(surface, fonts, mouse_pos):
    return ch3mod.draw_timeout(surface, fonts, mouse_pos)
''',
    "ch3_storm_intensity": '''def ch3_storm_intensity(ch3):
    return ch3mod.storm_intensity(ch3)
''',
}

for name, body in wrappers.items():
    # Find function start
    idx = text.find(f"def {name}(")
    if idx < 0:
        print("SKIP missing", name)
        continue
    # Find next top-level def or section after this
    next_def = re.search(r"\ndef [a-zA-Z_]", text[idx + 1 :])
    next_sec = re.search(r"\n# =====", text[idx + 1 :])
    end_rel = None
    candidates = []
    if next_def:
        candidates.append(next_def.start())
    if next_sec:
        candidates.append(next_sec.start())
    if not candidates:
        raise SystemExit(f"no end for {name}")
    end = idx + 1 + min(candidates)
    text = text[:idx] + body.strip() + "\n\n" + text[end:]
    print("OK", name)

# Remove obsolete try_ch2_wire_click if still present — keep as no-op bridge
if "def try_ch2_wire_click" in text:
    idx = text.find("def try_ch2_wire_click")
    next_def = re.search(r"\ndef [a-zA-Z_]", text[idx + 1 :])
    end = idx + 1 + next_def.start()
    text = (
        text[:idx]
        + "def try_ch2_wire_click(ch2, part):\n    \"\"\"Legacy no-op — wiring uses drag-and-snap.\"\"\"\n    return\n\n"
        + text[end:]
    )
    print("OK try_ch2_wire_click noop")

path.write_text(text, encoding="utf-8")
print("DONE", len(text))
