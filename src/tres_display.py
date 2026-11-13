"""Labwc-only output scaling, preserving the existing user autostart."""
from __future__ import annotations

import os
import re
import shlex
import tempfile
import shutil
import subprocess
from pathlib import Path

START = "# BEGIN TRES DISPLAY SCALE"
END = "# END TRES DISPLAY SCALE"
SCALE_BLOCK = re.compile(r"(?ms)^# BEGIN TRES DISPLAY SCALE\n.*?^# END TRES DISPLAY SCALE\n?")
_NAME = re.compile(r"[a-zA-Z0-9_.:-]+\Z")

_SCALE_COMMAND = re.compile(
    r"^\(sleep 1; wlr-randr --output ([A-Za-z0-9_.:-]+) "
    r"--scale ([0-9]+(?:\.[0-9]+)?)\)\s*(?:>/dev/null 2>&1\s*)?&$"
)


def saved_scales(text: str) -> dict[str, float]:
    """Read all existing Tres output scales, refusing to discard custom lines."""
    blocks = list(SCALE_BLOCK.finditer(text))
    if len(blocks) > 1 or (
        (START in text or END in text) and len(blocks) != 1
    ):
        raise DisplayError("Malformed or duplicate Tres scale block; left unchanged.")
    if not blocks:
        return {}
    scales = {}
    for raw in blocks[0].group().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _SCALE_COMMAND.fullmatch(line)
        if not match:
            raise DisplayError("Unrecognized command in saved display block; left unchanged.")
        scales[match.group(1)] = float(match.group(2))
    return scales


def persist_scales(path: Path, old: str, values: dict[str, float]) -> None:
    lines = [START, "# Tres display scales; one command per output."]
    for output, scale in sorted(values.items()):
        lines.append(
            f"(sleep 1; wlr-randr --output {shlex.quote(output)} "
            f"--scale {shlex.quote(f'{scale:g}')}) >/dev/null 2>&1 &"
        )
    lines.append(END)
    new_text = SCALE_BLOCK.sub("", old).rstrip("\n") + "\n" + "\n".join(lines) + "\n"
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o700
    fd, temporary = tempfile.mkstemp(prefix=".autostart-tres-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(new_text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)




class DisplayError(RuntimeError):
    pass


def parse_output_text(text: str) -> list[tuple[str, float]]:
    """Read the standard `wlr-randr` output, supported by older versions.

    Output headings have no leading whitespace (e.g. eDP-1 "Built-in
    display"). Indented property lines describe that output. Disabled
    outputs are intentionally omitted from the scale selector.
    """
    result: list[tuple[str, float]] = []
    name: str | None = None
    enabled: bool | None = None
    scale = 1.0
    saw_scale = False

    def complete() -> None:
        if name is not None and (enabled is True or (enabled is None and saw_scale)):
            result.append((name, scale))

    for line in text.splitlines():
        heading = re.fullmatch(
            r'([A-Za-z0-9][A-Za-z0-9_.:-]*)(?:\s+"[^"]*")?\s*',
            line,
        ) if line and not line[0].isspace() else None
        if heading:
            complete()
            name = heading.group(1)
            enabled = None
            scale = 1.0
            saw_scale = False
            continue
        if name is None:
            continue
        property_line = line.strip()
        if property_line.startswith("Enabled:"):
            enabled = property_line.split(":", 1)[1].strip().lower() == "yes"
        elif property_line.startswith("Scale:"):
            match = re.fullmatch(r"Scale:\s*([0-9]+(?:\.[0-9]+)?)", property_line)
            if not match:
                raise DisplayError(f"Invalid scale reported for {name}.")
            scale = float(match.group(1))
            saw_scale = True

    complete()
    return result


def output_info() -> list[tuple[str, float]]:
    if shutil.which("wlr-randr") is None:
        raise DisplayError("Install wlr-randr: sudo apt install wlr-randr")
    # No --json here: older distro packages do not support it, but the
    # plain-text output has been part of wlr-randr since early releases.
    try:
        proc = subprocess.run(["wlr-randr"], capture_output=True,
                              text=True, timeout=6, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DisplayError(str(error)) from error
    if proc.returncode:
        raise DisplayError((proc.stderr or
                            "Unable to query Wayland outputs.").strip())
    outputs = parse_output_text(proc.stdout)
    if not outputs:
        raise DisplayError(
            "No enabled displays were found in wlr-randr output. "
            "Check that you are running inside the Tres session."
        )
    return outputs


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
    path = autostart or Path.home() / ".config/tres/labwc/autostart"
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else "#!/bin/sh\n"
    if not old.startswith("#!"):
        raise DisplayError("Unexpected autostart file format; left unchanged.")
    values = saved_scales(old)
    values[output] = factor

    # Persist only after the compositor actually accepts the requested scale.
    if shutil.which("wlr-randr") is None:
        raise DisplayError("Install wlr-randr: sudo apt install wlr-randr")
    try:
        result = subprocess.run(
            ["wlr-randr", "--output", output, "--scale", f"{factor:g}"],
            capture_output=True, text=True, timeout=8, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DisplayError(f"Unable to set display scale: {error}") from error
    if result.returncode:
        raise DisplayError((result.stderr or "The compositor rejected the scale.").strip())
    persist_scales(path, old, values)
