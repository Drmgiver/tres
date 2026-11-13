"""Lightweight Wayland screenshot capture using grim and slurp (no portal)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class CaptureError(RuntimeError):
    """Capture failed with an actionable error."""


class CaptureCancelled(Exception):
    """The user cancelled the region selection."""


def capture(destination: str | Path, select_region: bool = False) -> Path:
    """Capture a whole screen or an interactively selected region as PNG.

    No shell interpolation. Slurp supplies the geometry directly to Grim.
    """
    if shutil.which("grim") is None:
        raise CaptureError("Grim is not installed. Install it with: sudo apt install grim")
    if select_region and shutil.which("slurp") is None:
        raise CaptureError("Slurp is not installed. Install it with: sudo apt install slurp")
    path = Path(destination).expanduser()
    args = ["grim"]
    if select_region:
        try:
            selection = subprocess.run(
                ["slurp"], capture_output=True, text=True, timeout=180, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise CaptureError(f"Could not select a screen region: {error}") from error
        if selection.returncode or not selection.stdout.strip():
            raise CaptureCancelled
        args.extend(["-g", selection.stdout.strip()])
    args.append(str(path))
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=45, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CaptureError(f"Could not take screenshot: {error}") from error
    if result.returncode:
        raise CaptureError(
            (result.stderr or result.stdout or "Grim could not capture the screen").strip()
        )
    return path
