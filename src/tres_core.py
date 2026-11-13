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


# Only these explicitly approved host power actions may be requested.
POWER_COMMANDS = {
    "restart": "reboot",
    "shutdown": "poweroff",
}


def request_power_action(action: str, timeout: float = 15.0) -> None:
    """Request a normal logind-managed reboot or poweroff, without sudo.

    Caller must obtain explicit user confirmation first. Never use `--force`:
    systemd/logind should handle active sessions, inhibitors and permissions.
    """
    if action not in POWER_COMMANDS:
        raise ValueError(f"Unsupported power action: {action}")
    try:
        result = subprocess.run(
            ["systemctl", POWER_COMMANDS[action]],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Could not request {action}: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or
                  "The system refused the power request").strip()
        raise RuntimeError(detail)



def submenu_pages(count: int, max_rows: int = 12) -> list[tuple[int, int]]:
    """Split a potentially tall GTK3/Wayland menu into bounded submenu ranges.

    The ranges are start-inclusive and end-exclusive. When a menu would have
    more than max_rows page links, each page covers a larger slice that can
    itself be divided recursively, keeping *every* menu level short.
    """
    if count < 0:
        raise ValueError("Menu item count must not be negative")
    if max_rows < 2:
        raise ValueError("Menu size must be at least two")
    if not count:
        return []
    if count <= max_rows:
        return [(0, count)]

    page_size = max_rows
    while (count + page_size - 1) // page_size > max_rows:
        page_size *= max_rows
    return [
        (start, min(start + page_size, count))
        for start in range(0, count, page_size)
    ]
