# -*- coding: utf-8 -*-
"""
updater.py — Background update checker.

Checks GitHub releases API on startup (after a 30s delay so the app is
fully loaded first). If a newer version is available, shows a tray balloon.
When the user clicks "Update", downloads the installer and runs it.
"""

import os
import sys
import threading
import tempfile
import urllib.request
import urllib.error
import json
import tkinter as tk
from tkinter import messagebox

from state import VERSION

GITHUB_API   = "https://api.github.com/repos/carlomazo/keep-awake/releases/latest"
CHECK_DELAY  = 30   # seconds after launch before first check
TIMEOUT      = 10   # HTTP timeout


def _parse_version(v: str):
    v = v.lstrip("v").split("-")[0]  # strip pre-release suffix e.g. "2.5.0-beta"
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0, 0, 0)


def _fetch_latest():
    req = urllib.request.Request(
        GITHUB_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "keep-awake-updater"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read().decode())
    tag     = data.get("tag_name", "")
    assets  = data.get("assets", [])
    # prefer setup installer, fall back to bare exe
    url = next(
        (a["browser_download_url"] for a in assets if "setup" in a["name"].lower()),
        next((a["browser_download_url"] for a in assets if a["name"].endswith(".exe")), None),
    )
    return tag, url


def _download_and_run(url: str, tag: str, notify_fn):
    notify_fn(f"Downloading Keep Awake {tag}…")
    suffix = ".exe"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.close()
    try:
        urllib.request.urlretrieve(url, tmp.name)
    except Exception as e:
        _show_error(f"Download failed: {e}")
        return
    os.startfile(tmp.name)


def _show_error(msg: str):
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Keep Awake — Update Error", msg)
    root.destroy()


def _prompt_update(tag: str, url: str, notify_fn):
    root = tk.Tk()
    root.withdraw()
    answer = messagebox.askyesno(
        "Keep Awake — Update Available",
        f"Version {tag} is available (you have {VERSION}).\n\nDownload and install now?",
    )
    root.destroy()
    if answer:
        threading.Thread(
            target=_download_and_run, args=(url, tag, notify_fn), daemon=True
        ).start()


def start_update_checker(notify_fn=None):
    """
    Spawn background thread that checks for updates once after CHECK_DELAY seconds.
    notify_fn(msg) should call the tray balloon notification.
    """
    def _check():
        import time
        time.sleep(CHECK_DELAY)
        try:
            tag, url = _fetch_latest()
        except Exception:
            return  # silently ignore network errors

        if not url:
            return
        if _parse_version(tag) <= _parse_version(VERSION):
            return

        if notify_fn:
            notify_fn(f"Keep Awake {tag} is available. Click to update.")

        _prompt_update(tag, url, notify_fn or (lambda m: None))

    threading.Thread(target=_check, daemon=True, name="update-checker").start()
