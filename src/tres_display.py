"""Labwc-only output scaling, preserving the existing user autostart."""
from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path

START = "# BEGIN TRES DISPLAY SCALE"
END = "# END TRES DISPLAY SCALE"
SCALE_BLOCK = re.compile(r"(?ms)^# BEGIN TRES DISPLAY SCALE\n.*?^# END TRES DISPLAY SCALE\n?")
_NAME = re.compile(r"[a-zA-Z0-9_.:-]+\Z")


class DisplayError(RuntimeError):
    pass


def output_info() -> list[tuple[str, float]]:
    if shutil.which("wlr-randr") is None:
        raise DisplayError("Install wlr-randr: sudo apt install wlr-randr")
    try:
        proc = subprocess.run(["wlr-randr", "--json"], capture_output=True,
                              text=True, timeout=6, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DisplayError(str(error)) from error
    if proc.returncode:
        raise DisplayError((proc.stderr or "Unable to query Wayland outputs").strip())
    try:
        data = json.loads(proc.stdout)
        if isinstance(data, dict):
            data = data.get("outputs", [])
        return [(str(o["name"]), float(o.get("scale", 1)))
                for o in data if o.get("enabled", True) and o.get("name")]
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise DisplayError("Unexpected output information from wlr-randr.") from error


def apply_scale(output: str, scale: float, autostart: Path | None = None) -> None:
    """Change only the requested Wayland output; persist only on success.

    The block is the same one written by scripts/set-scale.sh and coexists with
    the user's other autostart entries (including their original 150% scale).
    """
    if not _NAME.fullmatch(output) or output.startswith("-"):
        raise ValueError("Invalid output identifier.")
    try:
        factor = float(scale)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError("Invalid display scale.") from error
    if not 0.75 <= factor <= 3.0:
        raise ValueError("Display scale must be between 0.75 and 3.")
    if shutil.which("wlr-randr") is None:
        raise DisplayError("Install wlr-randr: sudo apt install wlr-randr")
    normalized = f"{factor:g}"
    try:
        result = subprocess.run(
            ["wlr-randr", "--output", output, "--scale", normalized],
            capture_output=True, text=True, timeout=8, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DisplayError(f"Unable to set display scale: {error}") from error
    if result.returncode:
        raise DisplayError((result.stderr or "The compositor rejected the scale.").strip())

    path = autostart or Path.home() / ".config/tres/labwc/autostart"
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else "#!/bin/sh\n"
    block = (f"{START}\n"
             "# Output scaling is set for Tres only, never for COSMIC.\n"
             f"(sleep 1; wlr-randr --output {shlex.quote(output)} "
             f"--scale {shlex.quote(normalized)}) >/dev/null 2>&1 &\n"
             f"{END}\n")
    clean = SCALE_BLOCK.sub("", old).rstrip("\n") + "\n"
    if not clean.startswith("#!"):
        raise DisplayError("Unexpected autostart file format; refusing to rewrite it.")
    path.write_text(clean + block, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o100)
