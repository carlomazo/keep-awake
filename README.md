# Keep Awake

A lightweight Windows system tray app that prevents your PC from sleeping or locking — with smart pause features so it stays out of your way when you don't need it.

No installer. No background services. Just run it.

---

## Features

### Core
- Prevents Windows sleep and screen-off via `SetThreadExecutionState`
- Optional mouse nudge (1px back-and-forth, returns to original position)
- Optional configurable key press (default: Scroll Lock)
- Green tray icon = active, red = paused
- Double-click tray icon to toggle

### Smart Pause
- **Meeting detection** — pauses automatically when MS Teams or Zoom is running
- **Battery guard** — pauses below a configurable battery threshold (default 20%), resumes on charger
- **Screen lock** — pauses when the screen locks, resumes when unlocked
- **Smart idle** — skips mouse nudge while you're actively typing or moving the mouse

### Schedule
- Up to 3 time blocks per day (e.g. 08:00–12:00 and 13:00–18:00)
- Per-day selection (Mon–Sun independently)
- Auto start/stop — app activates and pauses itself on schedule

### Profiles
- Save named configurations (interval, auto-stop, schedule)
- Switch profiles from the tray menu without opening Settings
- Double-click a profile to activate it directly

### Settings
- **General tab** — interval, auto-stop timer, keep-awake methods
- **Schedule tab** — time blocks and day selection
- **Profiles tab** — create, rename, reorder, activate profiles
- **System tab** — language (EN/PT-BR), theme (Dark/Light), hotkey, autostart, export/import config
- Changes apply immediately via Apply button (no restart needed)

### Log
- Usage log stored in `usage_log.csv` — every session recorded with date, start, end, duration
- Log viewer in Settings with List, Week, Month, and Chart views
- Export to standalone HTML report

### Other
- Configurable global hotkey (default `Ctrl+Shift+K`) to toggle from anywhere
- Start with Windows (registry autostart)
- Start paused option
- Single instance protection via Windows named mutex
- Balloon tip notifications on state changes

---

## Requirements

- Windows 10 or later
- Python 3.8+
- `pystray` library

```
pip install pystray
```

---

## Running

```
python keep_awake.py
```

Or use the included `start.bat` to launch minimized (no cmd window flash).

### First-time setup

```
setup.bat
```

Installs `pystray` and creates a shortcut in the Startup folder if you want autostart.

---

## Project Structure

```
keep_awake.py     — entry point: tray menu, start/stop, hotkey, orchestration
state.py          — AppState dataclass, settings load/save, shared singleton
core.py           — translations, tooltip, icon, ctypes helpers, schedule logic
monitors.py       — background loops: keep-awake, tooltip, schedule, meeting, battery, lock
settings_ui.py    — full Settings window (Tkinter)
tests/
  test_core.py    — 33 unit tests for core logic
```

---

## Keyboard Shortcut

Default: `Ctrl+Shift+K` — toggles keep-awake from any window.

Reassignable in **Settings > System > Hotkey**.

---

## Changelog

See [CHANGELOG.txt](CHANGELOG.txt) for full version history.
