"""Safely manage only Tres-owned key bindings in Labwc rc.xml."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import quoteattr

BEGIN = "<!-- BEGIN TRES SHORTCUTS -->"
END = "<!-- END TRES SHORTCUTS -->"
MARKED = re.compile(r"(?s)<!-- BEGIN TRES SHORTCUTS -->.*?<!-- END TRES SHORTCUTS -->")
KEY_PATTERN = re.compile(r"(?:(?:W|A|C|S)-)*[A-Za-z0-9_]+\Z")
DEFAULT_KEYS = {"screenshot": "Print", "files": "W-e", "terminal": "W-Return", "search": "W-space"}
COMMANDS = {"screenshot": "tres-screenshot", "files": "tres-open-files",
            "terminal": "tres-open-terminal", "search": "tres-search"}


def rc_path() -> Path:
    return Path.home() / ".config/tres/labwc/rc.xml"


def executable(name: str) -> str:
    local = Path.home() / ".local/bin" / name
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    return "/usr/bin/" + name


def read_shortcuts(path: Path | None = None) -> dict[str, str]:
    path = path or rc_path()
    try:
        old = path.read_text(encoding="utf-8")
    except OSError:
        return {name: "" for name in DEFAULT_KEYS}
    match = MARKED.search(old)
    if not match:
        return {name: "" for name in DEFAULT_KEYS}
    found = {name: "" for name in DEFAULT_KEYS}
    try:
        root = ET.fromstring("<keyboard>" + match.group(0) + "</keyboard>")
    except ET.ParseError:
        return {name: "" for name in DEFAULT_KEYS}
    for bind in root.findall("./keybind"):
        action = bind.find("action")
        if action is None:
            continue
        command = action.get("command", "")
        for name, binary in COMMANDS.items():
            if command.endswith("/" + binary):
                found[name] = bind.get("key", "")
    return found


def save_shortcuts(keys: dict[str, str], path: Path | None = None) -> None:
    if set(keys) != set(DEFAULT_KEYS):
        raise ValueError("Expected Screenshot, Files, Terminal, and Search shortcuts.")
    values = [val for val in keys.values() if val]
    if any(not KEY_PATTERN.fullmatch(value) for value in values):
        raise ValueError("Use Labwc key names like Print, W-e, or W-Return.")
    if len(set(values)) != len(values):
        raise ValueError("Two shortcuts cannot use the same key combination.")

    path = path or rc_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<labwc_config>\n  <keyboard>\n    <default />\n  </keyboard>\n</labwc_config>\n'
    )
    try:
        root = ET.fromstring(old)
    except ET.ParseError as error:
        raise ValueError(f"Labwc rc.xml is invalid; left unchanged: {error}") from error
    if root.tag != "labwc_config":
        raise ValueError("Unexpected Labwc rc.xml root; left unchanged.")

    block = [BEGIN]
    for name, command in COMMANDS.items():
        if not keys[name]:
            continue
        block.extend([
            f'  <keybind key={quoteattr(keys[name])}>',
            f'    <action name="Execute" command={quoteattr(executable(command))} />',
            "  </keybind>",
        ])
    block.append(END)
    managed = "\n".join(block)
    if MARKED.search(old):
        updated = MARKED.sub(lambda _: managed, old)
    elif re.search(r"</keyboard\s*>", old):
        updated = re.sub(r"</keyboard\s*>",
                         lambda _: "  " + managed + "\n  </keyboard>",
                         old, count=1)
    else:
        updated = re.sub(r"</labwc_config\s*>",
                         lambda _: "  <keyboard>\n    <default />\n    " +
                         managed + "\n  </keyboard>\n</labwc_config>",
                         old, count=1)
    try:
        ET.fromstring(updated)
    except ET.ParseError as error:
        raise ValueError(f"Shortcut XML could not be validated: {error}") from error
    if updated == old:
        return

    fd, temp = tempfile.mkstemp(prefix=".rc-tres-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(updated)
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def reload_labwc() -> None:
    if shutil.which("labwc") is None:
        raise RuntimeError("Labwc is not installed.")
    try:
        result = subprocess.run(["labwc", "--reconfigure"], capture_output=True,
                                text=True, timeout=6, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Could not reload Labwc: {error}") from error
    if result.returncode:
        raise RuntimeError((result.stderr or "Labwc could not reload the shortcuts.").strip())
