# -*- coding: utf-8 -*-
"""
monitors.py — Keep-awake loops and background monitors.

Imports: state (singleton), core (pure helpers).
The _shutdown threading.Event is created in keep_awake.py and imported here.
"""

import ctypes
import ctypes.wintypes
import csv
import datetime
import os
import subprocess
import threading
import time

from state import state, LOG_FILE
from core import (
    T,
    _build_tooltip,
    _get_idle_secs,
    _get_battery_percent,
    _in_schedule_window,
)

# ---------------------------------------------------------------------------
# _shutdown event — set by keep_awake.py; monitors check it to exit cleanly.
# Initialised here as a fallback so the module can be imported standalone.
# keep_awake.py replaces this reference by assigning monitors._shutdown.
# ---------------------------------------------------------------------------
_shutdown = threading.Event()


# ---------------------------------------------------------------------------
# Keep-awake primitives
# ---------------------------------------------------------------------------

def move_mouse_slightly():
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    x, y = pt.x, pt.y
    ctypes.windll.user32.SetCursorPos(x + 1, y)
    time.sleep(0.05)
    ctypes.windll.user32.SetCursorPos(x, y)


def simulate_key_press():
    ctypes.windll.user32.keybd_event(state.nudge_key_vk, 0, 0, 0)
    ctypes.windll.user32.keybd_event(state.nudge_key_vk, 0, 0x0002, 0)


def reset_idle_timer():
    if state.keep_api:
        ES_CONTINUOUS       = 0x80000000
        ES_SYSTEM_REQUIRED  = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )


def restore_idle_timer():
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


# ---------------------------------------------------------------------------
# Usage log
# ---------------------------------------------------------------------------

def _log_session(start_dt, end_dt):
    duration_secs = int((end_dt - start_dt).total_seconds())
    if duration_secs < 5:
        return
    write_header = not os.path.exists(LOG_FILE)
    try:
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["date", "start", "end", "duration_min"])
            w.writerow([
                start_dt.strftime("%Y-%m-%d"),
                start_dt.strftime("%H:%M:%S"),
                end_dt.strftime("%H:%M:%S"),
                round(duration_secs / 60, 1),
            ])
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Notification helper
# ---------------------------------------------------------------------------

def notify(icon, message):
    try:
        icon.notify(message, "Keep Awake")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main keep-awake loop
# ---------------------------------------------------------------------------

def keep_awake_loop(icon):
    while state.running and not _shutdown.is_set():
        reset_idle_timer()
        if state.smart_pause and _get_idle_secs() < state.smart_pause_secs:
            if _shutdown.wait(timeout=state.interval):
                break
            continue
        if state.keep_mouse:
            move_mouse_slightly()
        if state.keep_key:
            simulate_key_press()
        if _shutdown.wait(timeout=state.interval):
            break


# ---------------------------------------------------------------------------
# Tooltip refresh loop
# ---------------------------------------------------------------------------

_tooltip_loop_running = False


def tooltip_loop(icon):
    global _tooltip_loop_running
    if _tooltip_loop_running:
        return
    _tooltip_loop_running = True
    while not _shutdown.is_set():
        if _shutdown.wait(timeout=10):
            break
        icon.title = _build_tooltip()
    _tooltip_loop_running = False


# ---------------------------------------------------------------------------
# Schedule loop
# ---------------------------------------------------------------------------

def schedule_loop(icon):
    # Import here to avoid circular import at module level
    import keep_awake as _ka
    while state.schedule_enabled and not _shutdown.is_set():
        should_run = _in_schedule_window()
        if should_run and not state.running:
            _ka.start_keeping(icon, None)
        elif not should_run and state.running:
            _ka.stop_keeping(icon, None)
        # Check every 10 s; bail out quickly if schedule disabled or shutdown
        for _ in range(6):
            if not state.schedule_enabled or _shutdown.is_set():
                return
            if _shutdown.wait(timeout=10):
                return


def _start_schedule_thread(icon):
    if state.schedule_thread and state.schedule_thread.is_alive():
        return
    state.schedule_thread = threading.Thread(
        target=schedule_loop, args=(icon,), daemon=True)
    state.schedule_thread.start()


# ---------------------------------------------------------------------------
# Meeting monitor
# ---------------------------------------------------------------------------

_MEETING_PROCS = {"ms-teams.exe", "ms-teams (new).exe", "zoom.exe"}


def _is_in_meeting():
    try:
        out = subprocess.check_output(
            ["tasklist", "/FO", "CSV", "/NH"], text=True, stderr=subprocess.DEVNULL)
        procs = {line.split('","')[0].strip('"').lower() for line in out.splitlines() if line}
        return bool(procs & _MEETING_PROCS)
    except Exception:
        return False


_meeting_thread = None


def _meeting_monitor_loop(icon):
    import keep_awake as _ka
    while state.meeting_detection and not _shutdown.is_set():
        in_meeting = _is_in_meeting()
        if in_meeting and not state.meeting_active:
            state.meeting_was_running = state.running
            state.meeting_active = True
            if state.running:
                _ka.stop_keeping(icon, None)
                notify(icon, T("Meeting detected — Keep Awake paused"))
            icon.title = _build_tooltip()
        elif not in_meeting and state.meeting_active:
            state.meeting_active = False
            if state.meeting_was_running:
                _ka.start_keeping(icon, None)
                notify(icon, T("Meeting ended — Keep Awake resumed"))
            icon.title = _build_tooltip()
        if _shutdown.wait(timeout=30):
            break


def _start_meeting_monitor(icon):
    global _meeting_thread
    if _meeting_thread and _meeting_thread.is_alive():
        return
    _meeting_thread = threading.Thread(
        target=_meeting_monitor_loop, args=(icon,), daemon=True)
    _meeting_thread.start()


# ---------------------------------------------------------------------------
# Battery guard
# ---------------------------------------------------------------------------

_battery_thread = None


def _battery_monitor_loop(icon):
    import keep_awake as _ka
    while state.battery_guard and not _shutdown.is_set():
        pct = _get_battery_percent()
        if pct is not None and pct <= state.battery_threshold and not state.battery_paused:
            state.battery_was_running = state.running
            state.battery_paused = True
            if state.running:
                _ka.stop_keeping(icon, None)
                notify(icon, T("Battery at % — Keep Awake paused").format(pct=pct))
            icon.title = _build_tooltip()
        elif (pct is None or pct > state.battery_threshold) and state.battery_paused:
            state.battery_paused = False
            if state.battery_was_running:
                _ka.start_keeping(icon, None)
                notify(icon, T("Charging — Keep Awake resumed"))
            icon.title = _build_tooltip()
        if _shutdown.wait(timeout=30):
            break


def _start_battery_monitor(icon):
    global _battery_thread
    if _battery_thread and _battery_thread.is_alive():
        return
    _battery_thread = threading.Thread(
        target=_battery_monitor_loop, args=(icon,), daemon=True)
    _battery_thread.start()


# ---------------------------------------------------------------------------
# Lock screen guard
# ---------------------------------------------------------------------------

_lock_thread = None


def _is_screen_locked():
    hdesk = ctypes.windll.user32.OpenDesktopW("Default", 0, False, 0x0100)
    if not hdesk:
        return False
    result = ctypes.windll.user32.SwitchDesktop(hdesk)
    ctypes.windll.user32.CloseDesktop(hdesk)
    return not result


def _lock_monitor_loop(icon):
    import keep_awake as _ka
    while state.lock_guard and not _shutdown.is_set():
        locked = _is_screen_locked()
        if locked and not state.lock_paused:
            state.lock_was_running = state.running
            state.lock_paused = True
            if state.running:
                _ka.stop_keeping(icon, None)
                notify(icon, T("Screen locked — Keep Awake paused"))
            icon.title = _build_tooltip()
        elif not locked and state.lock_paused:
            state.lock_paused = False
            if state.lock_was_running:
                _ka.start_keeping(icon, None)
                notify(icon, T("Screen unlocked — Keep Awake resumed"))
            icon.title = _build_tooltip()
        if _shutdown.wait(timeout=5):
            break


def _start_lock_monitor(icon):
    global _lock_thread
    if _lock_thread and _lock_thread.is_alive():
        return
    _lock_thread = threading.Thread(
        target=_lock_monitor_loop, args=(icon,), daemon=True)
    _lock_thread.start()
