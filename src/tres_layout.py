"""Persistent Tres three-square stacking preference (no GTK dependency)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

MODES = ("under", "over", "reserved")
DEFAULT_MODE = "under"


def mode_path() -> Path:
    """Use Tres's own configuration, never Labwc/COSMIC's shared settings."""
    root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return root / "tres" / "panel-mode"


def read_mode(path: Path | None = None) -> str:
    path = Path(path) if path is not None else mode_path()
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return DEFAULT_MODE
    return value if value in MODES else DEFAULT_MODE


def save_mode(mode: str, path: Path | None = None) -> None:
    """Atomically save a known-good preference. Invalid settings never persist."""
    if mode not in MODES:
        raise ValueError(f"Unknown Tres stacking mode: {mode}")
    path = Path(path) if path is not None else mode_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".panel-mode-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(mode + "\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
