"""Tres panel screen-edge placement and precise pixel offsets (GTK-independent)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

EDGES = ("top", "bottom", "left", "right")
DEFAULT_POSITION = {"edge": "top", "x": 0, "y": 0}
EDGE_MARGIN = 3
SQUARE_SPACING = 5


def position_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return root / "tres" / "panel-position.json"


def validate_position(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != {"edge", "x", "y"}:
        raise ValueError("Invalid Tres panel position.")
    if value["edge"] not in EDGES:
        raise ValueError("Unknown panel edge.")
    for axis in ("x", "y"):
        coordinate = value[axis]
        if type(coordinate) is not int or not -20000 <= coordinate <= 20000:
            raise ValueError("Panel offsets must be integer pixels within +/-20000.")
    return dict(value)


def read_position(path: Path | None = None) -> dict:
    path = Path(path) if path is not None else position_path()
    try:
        return validate_position(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return dict(DEFAULT_POSITION)


def save_position(value: dict, path: Path | None = None) -> None:
    settings = validate_position(value)
    path = Path(path) if path is not None else position_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".panel-position-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(settings, stream, sort_keys=True)
            stream.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def panel_size(square_size: int) -> tuple[int, int]:
    return square_size * 3 + 2 * SQUARE_SPACING, square_size


def origin(edge: str, panel_width: int, panel_height: int,
           monitor_width: int, monitor_height: int) -> tuple[int, int]:
    """Exact centered default: middle square's center is at monitor center."""
    if edge not in EDGES:
        raise ValueError("Unknown panel edge.")
    if edge in ("top", "bottom"):
        return ((monitor_width - panel_width) // 2,
                EDGE_MARGIN if edge == "top" else monitor_height - panel_height - EDGE_MARGIN)
    return (EDGE_MARGIN if edge == "left" else monitor_width - panel_width - EDGE_MARGIN,
            (monitor_height - panel_height) // 2)


def coordinates(position: dict, panel_width: int, panel_height: int,
                monitor_width: int, monitor_height: int) -> tuple[int, int]:
    """Screen-relative position, clamped to keep all squares visible."""
    position = validate_position(position)
    base_x, base_y = origin(position["edge"], panel_width, panel_height,
                            monitor_width, monitor_height)
    return (max(0, min(max(0, monitor_width - panel_width), base_x + position["x"])),
            max(0, min(max(0, monitor_height - panel_height), base_y + position["y"])))


def with_coordinates(edge: str, x: int, y: int, panel_width: int,
                     panel_height: int, monitor_width: int, monitor_height: int) -> dict:
    """Convert a dragged pixel position into persistent offsets from the selected edge."""
    base_x, base_y = origin(edge, panel_width, panel_height, monitor_width, monitor_height)
    return validate_position({"edge": edge, "x": int(x - base_x), "y": int(y - base_y)})
