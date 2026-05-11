# -*- coding: utf-8 -*-
"""
state.py — AppState singleton + settings persistence.

No imports from other keep-awake modules (avoids circular imports).
"""

import os
import json
import threading
from dataclasses import dataclass, field
from typing import Optional

# --- Paths ---

VERSION       = "2.5.0"

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
LOG_FILE      = os.path.join(BASE_DIR, "usage_log.csv")
MUTEX_NAME    = "Global\\KeepAwakeSingleInstance"


# --- AppState dataclass ---

@dataclass
class AppState:
    # Core
    running: bool = False
    interval: int = 60
    active_since: Optional[float] = None
    active_since_dt: Optional[object] = None
    auto_stop_after: Optional[int] = None
    auto_stop_timer: Optional[threading.Timer] = None

    # Schedule
    schedule_enabled: bool = False
    schedule_blocks: list = field(default_factory=lambda: [{"start": [8, 0], "end": [18, 0]}])
    schedule_days: set = field(default_factory=lambda: {0, 1, 2, 3, 4})
    schedule_thread: Optional[threading.Thread] = None

    # Profiles
    profiles: dict = field(default_factory=dict)
    active_profile: Optional[str] = None

    # Appearance
    theme: str = "light"
    language: str = "en"

    # Hotkey
    hotkey_mods: int = 0x0002 | 0x0004  # MOD_CONTROL | MOD_SHIFT
    hotkey_vk: int = 0x4B               # K

    # Meeting detection
    meeting_detection: bool = False
    meeting_active: bool = False
    meeting_was_running: bool = False

    # Smart pause
    smart_pause: bool = False
    smart_pause_secs: int = 30

    # Battery guard
    battery_guard: bool = False
    battery_threshold: int = 20
    battery_paused: bool = False
    battery_was_running: bool = False

    # Lock guard
    lock_guard: bool = False
    lock_paused: bool = False
    lock_was_running: bool = False

    # Keep methods
    keep_api: bool = True
    keep_mouse: bool = True
    keep_key: bool = False
    nudge_key_vk: int = 0x91  # Scroll Lock

    # Launch behavior
    start_paused: bool = False


# --- Module-level singleton ---

state = AppState()


# --- Settings persistence ---

def _settings_to_dict():
    return {
        "interval":           state.interval,
        "auto_stop_after":    state.auto_stop_after,
        "schedule_enabled":   state.schedule_enabled,
        "schedule_blocks":    state.schedule_blocks,
        "schedule_days":      sorted(state.schedule_days),
        "profiles":           state.profiles,
        "active_profile":     state.active_profile,
        "theme":              state.theme,
        "language":           state.language,
        "hotkey_mods":        state.hotkey_mods,
        "hotkey_vk":          state.hotkey_vk,
        "meeting_detection":  state.meeting_detection,
        "smart_pause":        state.smart_pause,
        "smart_pause_secs":   state.smart_pause_secs,
        "battery_guard":      state.battery_guard,
        "battery_threshold":  state.battery_threshold,
        "lock_guard":         state.lock_guard,
        "keep_api":           state.keep_api,
        "keep_mouse":         state.keep_mouse,
        "keep_key":           state.keep_key,
        "nudge_key_vk":       state.nudge_key_vk,
        "start_paused":       state.start_paused,
    }


def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_settings_to_dict(), f, indent=2)
    except Exception:
        pass


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            d = json.load(f)
        state.interval          = d.get("interval", 60)
        state.auto_stop_after   = d.get("auto_stop_after", None)
        state.schedule_enabled  = d.get("schedule_enabled", False)
        if "schedule_blocks" in d:
            state.schedule_blocks = d["schedule_blocks"]
        elif "schedule_start" in d and "schedule_end" in d:
            state.schedule_blocks = [{"start": d["schedule_start"], "end": d["schedule_end"]}]
        state.schedule_days     = set(d.get("schedule_days") or [0, 1, 2, 3, 4])
        state.profiles          = d.get("profiles", {})
        state.active_profile    = d.get("active_profile", None)
        state.theme             = d.get("theme", "light")
        state.language          = d.get("language", "en")
        state.hotkey_mods       = d.get("hotkey_mods", 0x0002 | 0x0004)
        state.hotkey_vk         = d.get("hotkey_vk",   0x4B)
        state.meeting_detection = d.get("meeting_detection", False)
        state.smart_pause       = d.get("smart_pause", False)
        state.smart_pause_secs  = d.get("smart_pause_secs", 30)
        state.battery_guard     = d.get("battery_guard", False)
        state.battery_threshold = d.get("battery_threshold", 20)
        state.lock_guard        = d.get("lock_guard", False)
        state.keep_api          = d.get("keep_api",      True)
        state.keep_mouse        = d.get("keep_mouse",    True)
        state.keep_key          = d.get("keep_key",      False)
        state.nudge_key_vk      = d.get("nudge_key_vk",  0x91)
        state.start_paused      = d.get("start_paused",  False)
    except Exception:
        pass
