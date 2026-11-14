"""One-shot patcher: point main.py challenge APIs at redesigned modules."""

from pathlib import Path

path = Path(r"C:\MarsMission\main.py")
text = path.read_text(encoding="utf-8")

def rep(old: str, new: str, label: str):
    global text
    if old not in text:
        raise SystemExit(f"MISSING: {label}")
    text = text.replace(old, new, 1)
    print("OK", label)


rep(
    '''def make_challenge1_state():
    """Fresh values every time Challenge 1 starts or restarts."""
    return {
        "phase": "ready",          # ready -> scanning -> results
        "scan_angle": 0.0,         # sweeping radar beam (degrees)
        "scan_progress": 0.0,      # 0 to 1 while scanning
        "hint": "",
        "antenna_angle": ANTENNA_START_ANGLE,
        "points_awarded": False,
        "time_left": float(CH1_TIME_LIMIT),
        "finish_time_left": 0,
        "connection_restored": False,
        "restore_delay": 0.0,  # short pause so kids can read the success message
    }''',
    '''def make_challenge1_state():
    """Fresh Challenge 1 state (radar tracking + antenna packets)."""
    return ch1mod.make_state()''',
    "ch1 state",
)

rep(
    '''def signal_strength(angle):
    """How strong the signal is (0-100). Closest to +20 is best."""
    distance = abs(angle - ANTENNA_TARGET_ANGLE)
    # Every degree away from the target lowers the bar
    strength = max(0, 100 - distance * 2)
    return strength''',
    '''def signal_strength(angle):
    """How strong the signal is (0-100). Closest to +20 is best."""
    return ch1mod.signal_strength(angle)''',
    "signal_strength",
)

rep(
    '''def make_challenge2_state():
    """Fresh values every time Challenge 2 starts or restarts."""
    return {
        "time_left": float(CH2_TIME_LIMIT),
        "finish_time_left": 0.0,
        "selected": None,              # first component the player clicked
        "hint": "",
        "wire_solar_battery": False,   # Solar Panel → Battery
        "wire_battery_habitat": False, # Battery → Mars Habitat
        "wires_done": False,
        "wire_success_delay": 0.0,
        # Power allocations (must add up to at most 80)
        "life": 20,
        "food": 20,
        "comms": 40,
        "food_freshness": 100.0,
        "points_awarded": False,
        "completed": False,
        "complete_delay": 0.0,
    }''',
    '''def make_challenge2_state():
    """Fresh Challenge 2 state (drag cables + power board)."""
    return ch2mod.make_state()''',
    "ch2 state",
)

rep(
    '''def ch2_total_power(ch2):
    """Add up all power currently given to the three systems."""
    return ch2["life"] + ch2["food"] + ch2["comms"]


def ch2_power_ok(ch2):
    """True when every system has at least its minimum power."""
    return ch2["life"] >= 30 and ch2["food"] >= 30 and ch2["comms"] >= 10


def ch2_change_power(ch2, system, delta):
    """Move power up or down by 10. Never go below 0 or above the budget."""
    new_value = ch2[system] + delta
    if new_value < 0:
        return
    # Pretend we made the change, then check the total still fits
    old = ch2[system]
    ch2[system] = new_value
    if ch2_total_power(ch2) > CH2_ENERGY_BUDGET:
        ch2[system] = old  # undo — not enough energy left''',
    '''def ch2_total_power(ch2):
    return ch2mod.total_power(ch2)


def ch2_power_ok(ch2):
    return ch2mod.power_ok(ch2)


def ch2_change_power(ch2, system, delta):
    ch2mod.change_power(ch2, system, delta)''',
    "ch2 power helpers",
)

rep(
    '''def rotate_antenna(ch1, direction):
    """Turn the antenna left (-1) or right (+1) by 5 degrees."""
    if ch1["connection_restored"]:
        return
    ch1["antenna_angle"] += direction * ANTENNA_STEP
    # Keep the dish in a sensible range so kids do not spin forever
    ch1["antenna_angle"] = max(-60, min(60, ch1["antenna_angle"]))''',
    '''def rotate_antenna(ch1, direction):
    """Turn the antenna left (-1) or right (+1) by 5 degrees."""
    ch1mod.rotate_antenna(ch1, direction)''',
    "rotate_antenna",
)

path.write_text(text, encoding="utf-8")
print("WROTE", path)
