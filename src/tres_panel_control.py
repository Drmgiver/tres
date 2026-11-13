#!/usr/bin/python3
"""Explicitly restart the Tres panel under its session supervisor."""
from __future__ import annotations

import os
import signal
import sys
from pathlib import Path


class PanelControlError(RuntimeError):
    pass


def pid_path() -> Path:
    return Path(os.environ.get("XDG_RUNTIME_DIR") or Path.home() / ".cache/tres") / "tres-panel.pid"


def restart_panel(path: Path | None = None) -> None:
    path = path or pid_path()
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
        if pid <= 1:
            raise ValueError("Invalid PID")
        process = Path("/proc") / str(pid)
        if process.stat().st_uid != os.getuid():
            raise PanelControlError("Panel process belongs to another user.")
        cmdline = (process / "cmdline").read_bytes().replace(b"\0", b" ")
        if b"tres_panel.py" not in cmdline:
            raise PanelControlError("The recorded process is not the Tres panel.")
        os.kill(pid, signal.SIGTERM)
    except (OSError, ValueError) as error:
        raise PanelControlError(
            "No supervised Tres panel was found. Log out and back in once "
            "after installing the panel recovery update."
        ) from error


def main() -> None:
    if sys.argv[1:] != ["restart"]:
        sys.exit("Usage: tres-panel-control restart")
    try:
        restart_panel()
    except PanelControlError as error:
        sys.exit(f"Unable to restart Tres panel: {error}")


if __name__ == "__main__":
    main()
