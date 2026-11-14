# MarsMission — Setup & Run

## Requirements

- **Python 3.10+** (3.10, 3.11, or 3.12 recommended)
- Internet once (to install packages)

## 1. Download / open the project

Unzip or clone so you have a folder like:

```text
MarsMission/
  main.py
  requirements.txt
  systems/
  assets/
  ...
```

## 2. Open a terminal in the project folder

**Windows (PowerShell or Command Prompt):**

```bat
cd path\to\MarsMission
```

**macOS / Linux:**

```bash
cd path/to/MarsMission
```

## 3. (Recommended) Create a virtual environment

**Windows:**

```bat
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

This installs **Pygame CE** (`pygame-ce`), which is imported in code as `import pygame`.

> If `pygame-ce` fails on your platform, you can try:  
> `python -m pip install pygame`  
> Do not install both `pygame` and `pygame-ce` in the same environment.

## 5. Run the game (development)

```bash
python main.py
```

On some systems:

```bash
python3 main.py
```

## 6. Packaged desktop builds (no Python required for players)

See `packaging/README.md`.

**Windows (build on Windows):**

```powershell
.\packaging\build_windows.ps1 -Mode RELEASE
# Output: dist\MARSMISSION\MARSMISSION.exe
# Zip:    releases\windows\MARSMISSION_Windows.zip
```

**macOS (build on a Mac):**

```bash
chmod +x packaging/build_macos.sh
./packaging/build_macos.sh RELEASE
```

Player instructions: `PLAYER_README.md`

## Controls (quick start)

| Key | Action |
|-----|--------|
| WASD / Arrows | Move (base) / drive (Mission 3) |
| E | Interact / collect / rescue |
| I | Inventory |
| J | Journal |
| ESC | Pause / back |
| Mouse | Menus, research, workbenches |

## Saves

Campaign progress is stored outside the project folder:

- **Windows:** `%LOCALAPPDATA%\MarsMission\`
- **macOS:** `~/Library/Application Support/MarsMission/`
- **Linux:** `~/.local/share/MarsMission/`

## Optional checks

```bash
python -c "import pygame; print(pygame.version.ver)"
python -m unittest discover -s tests -p "tests_*.py" -q
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python` not found | Install Python from python.org and tick “Add to PATH” |
| `No module named pygame` | Run `pip install -r requirements.txt` again inside the venv |
| Black / no window | Update GPU drivers; try another Python version (3.10–3.12) |
| Wrong folder | You must run `python main.py` from the folder that contains `main.py` |
