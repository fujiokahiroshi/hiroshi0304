from __future__ import annotations

import json
import os
import socket
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "runtime"
STATE_FILE = RUNTIME_DIR / "state.json"
JOBS_DIR = ROOT / "jobs"
VIEWER_HOST = "127.0.0.1"
VIEWER_PORT = 3939


def initial_state() -> dict[str, Any]:
    return {
        "status": "idle",
        "title": "CAD Workbench",
        "message": "ClaudeからのCAD指示を待っています",
        "steps": [],
        "current_step": -1,
        "job_dir": None,
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def read_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return initial_state()
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return initial_state()


def write_state(**updates: Any) -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    state = read_state()
    state.update(updates)
    state["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    fd, temporary = tempfile.mkstemp(prefix="state-", suffix=".json", dir=RUNTIME_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, STATE_FILE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return state


def viewer_reachable(timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((VIEWER_HOST, VIEWER_PORT), timeout=timeout):
            return True
    except OSError:
        return False
