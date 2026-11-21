"""hosted.py - everything for the public link (CLEARTRACE_HOSTED=1).

Each visitor gets a private sandbox: a fresh copy of a fake laptop.
Visitors can never see or touch real server files.
"""
import os
import shutil
import tempfile
import threading
import time

import make_demo

HOSTED = os.getenv("CLEARTRACE_HOSTED") == "1"

BASE = os.path.join(tempfile.gettempdir(), "cleartrace_sandboxes")
TEMPLATE = os.path.join(tempfile.gettempdir(), "cleartrace_template", "Alex's laptop")
LAPTOP_NAME = "Alex's laptop"
SANDBOX_MAX_AGE = 2 * 3600         # delete sandboxes (and uploads) after 2 hours
AI_CALLS_PER_VISITOR = 12           # about 6 messages per visitor
AI_CALLS_PER_HOUR = 600             # whole-site cap, protects the $150
MAX_UPLOAD_FILES = 20

_lock = threading.Lock()
_room = {"sensitive": 0, "freed_mb": 0.0, "visitors": 0}
_ai_hits = []


def _template():
    with _lock:
        if not os.path.isdir(TEMPLATE):
            make_demo.main(TEMPLATE)
    return TEMPLATE


def _cleanup():
    if not os.path.isdir(BASE):
        return
    now = time.time()
    for name in os.listdir(BASE):
        path = os.path.join(BASE, name)
        try:
            if now - os.path.getmtime(path) > SANDBOX_MAX_AGE:
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass


def new_sandbox():
    """Copy the fake laptop into a fresh private folder. Returns its path."""
    template = _template()
    _cleanup()
    os.makedirs(BASE, exist_ok=True)
    box = tempfile.mkdtemp(prefix="v_", dir=BASE)
    laptop = os.path.join(box, LAPTOP_NAME)

    def link_or_copy(src, dst):
        try:
            os.link(src, dst)          # hard link: instant, no extra disk space
        except OSError:
            shutil.copy2(src, dst)

    shutil.copytree(template, laptop, copy_function=link_or_copy)
    with _lock:
        _room["visitors"] += 1
    return laptop


def inside(path, sandbox):
    """True if path is inside the visitor's own sandbox."""
    root = os.path.realpath(os.path.dirname(sandbox))
    return os.path.realpath(path).startswith(root + os.sep)


def delete(path, sandbox):
    """Hosted delete: move to the sandbox's own hidden bin (never real files)."""
    if not inside(path, sandbox) or not os.path.isfile(path):
        return {"ok": False, "message": "File not found (maybe already deleted)."}
    size_mb = os.path.getsize(path) / (1024 * 1024)
    trash = os.path.join(os.path.dirname(sandbox), ".trash")
    os.makedirs(trash, exist_ok=True)
    os.replace(path, os.path.join(trash, f"{time.time_ns()}_{os.path.basename(path)}"))
    return {"ok": True, "message": f"Moved {os.path.basename(path)} to the Recycle Bin.",
            "freed_mb": size_mb}


def save_uploads(files, sandbox):
    """Save uploaded files into the sandbox's Uploads folder."""
    folder = os.path.join(sandbox, "Uploads")
    os.makedirs(folder, exist_ok=True)
    saved = 0
    for f in files[:MAX_UPLOAD_FILES]:
        name = os.path.basename(f.name).lstrip(".") or "file"
        with open(os.path.join(folder, name), "wb") as out:
            out.write(f.getbuffer())
        saved += 1
    return folder, saved


def ai_allowed(visitor_calls):
    """Per-visitor and whole-site caps on Claude calls."""
    if visitor_calls >= AI_CALLS_PER_VISITOR:
        return False
    now = time.time()
    with _lock:
        while _ai_hits and now - _ai_hits[0] > 3600:
            _ai_hits.pop(0)
        if len(_ai_hits) >= AI_CALLS_PER_HOUR:
            return False
        _ai_hits.append(now)
        return True


def add_room(sensitive=0, freed_mb=0.0):
    with _lock:
        _room["sensitive"] += sensitive
        _room["freed_mb"] += freed_mb


def room():
    with _lock:
        return dict(_room)
