"""Tres-only appearance and terminal preferences; no GTK or compositor imports."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

DEFAULT_APPEARANCE = {
    "square_color": "#ffffff",
    "hover_color": "#d8d8d8",
    "square_size": 19,
    "wallpaper_color": "#141414",
}
TERMINALS = ("foot", "terminator", "alacritty", "kitty", "gnome-terminal",
             "xfce4-terminal", "xterm", "cosmic-term")
_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")


def tres_path() -> Path:
    return Path.home() / ".config" / "tres"


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_appearance(settings: dict) -> dict:
    """Reject invalid appearance values, including dangerous CSS fragments."""
    if set(settings) != set(DEFAULT_APPEARANCE):
        raise ValueError("All four appearance properties must be supplied.")
    value = {}
    for key in ("square_color", "hover_color", "wallpaper_color"):
        color = settings[key]
        if not isinstance(color, str) or not _COLOR.fullmatch(color):
            raise ValueError("Colors must use six-digit hexadecimal RGB values.")
        value[key] = color.lower()
    size = settings["square_size"]
    if isinstance(size, bool) or not isinstance(size, int) or not 15 <= size <= 40:
        raise ValueError("Square size must be between 15 and 40 pixels.")
    value["square_size"] = size
    return value


def read_appearance(path: Path | None = None) -> dict:
    path = path or tres_path() / "appearance.json"
    raw = _read_json(path)
    result = dict(DEFAULT_APPEARANCE)
    for key, val in raw.items():
        if key in result:
            try:
                validate_appearance({**DEFAULT_APPEARANCE, key: val})
            except ValueError:
                continue
            result[key] = val
    return validate_appearance(result)


def save_appearance(settings: dict, path: Path | None = None) -> None:
    _write_json(path or tres_path() / "appearance.json", validate_appearance(settings))


def read_terminal(path: Path | None = None) -> str:
    path = path or tres_path() / "terminal"
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return "auto"
    return value if value in TERMINALS else "auto"


def save_terminal(terminal: str, path: Path | None = None) -> None:
    if terminal not in ("auto", *TERMINALS):
        raise ValueError("Unrecognized terminal application.")
    path = path or tres_path() / "terminal"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".terminal-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(terminal + "\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
