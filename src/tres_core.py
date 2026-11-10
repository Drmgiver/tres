"""Non-GUI pieces for Tres, kept independently testable."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Toplevel:
    app_id: str
    title: str


def parse_toplevels(output: str) -> list[Toplevel]:
    """Read wlrctl's `toplevel list` display: 'app_id: window title'.

    Preserve colons within window titles. Avoid treating empty output as a window.
    """
    result: list[Toplevel] = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or ": " not in line:
            continue
        app_id, title = line.split(": ", 1)
        if not (app_id := app_id.strip()) or not (title := title.strip()):
            continue
        result.append(Toplevel(app_id, title))
    return result


def windows(timeout: float = 3.0) -> list[Toplevel]:
    if not shutil.which("wlrctl"):
        raise RuntimeError("wlrctl is missing; install the wlrctl package")
    proc = subprocess.run(["wlrctl", "toplevel", "list"], capture_output=True,
                          text=True, timeout=timeout, check=False)
    if proc.returncode:
        raise RuntimeError((proc.stderr or "wlrctl could not query windows").strip())
    return parse_toplevels(proc.stdout)


def activate(window: Toplevel, timeout: float = 3.0) -> None:
    """Activate matching Wayland toplevel. No shell is involved."""
    proc = subprocess.run(["wlrctl", "window", "focus", f"app_id:{window.app_id}",
                           f"title:{window.title}"], capture_output=True,
                          text=True, timeout=timeout, check=False)
    if proc.returncode:
        raise RuntimeError((proc.stderr or "Unable to activate window").strip())
