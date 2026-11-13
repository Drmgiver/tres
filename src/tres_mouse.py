"""Tres-only Labwc mouse bindings for Super+drag on the layer-shell panel.

Labwc's default Frame W-Left bindings consume Super+left mouse events before
GTK can receive them. Free those bindings in Tres only, moving ordinary-window
dragging to Alt+left. Never overwrite a user's explicit mouse bindings.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

BEGIN = "<!-- BEGIN TRES PANEL DRAG -->"
END = "<!-- END TRES PANEL DRAG -->"
MARKED = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)

BLOCK = """<!-- BEGIN TRES PANEL DRAG -->
    <context name="Frame">
      <!-- Forward Super+Left to Tres's GTK layer-shell drag gesture. -->
      <mousebind button="W-Left" action="Press" />
      <mousebind button="W-Left" action="Drag" />
      <!-- Preserve compositor window dragging with Alt+Left instead. -->
      <mousebind button="A-Left" action="Press">
        <action name="Focus" />
        <action name="Raise" />
      </mousebind>
      <mousebind button="A-Left" action="Drag">
        <action name="Move" />
      </mousebind>
    </context>
<!-- END TRES PANEL DRAG -->"""


def configure(path: Path) -> str:
    path = Path(path)
    if path.is_symlink():
        return "skip-symlink"
    text = (path.read_text(encoding="utf-8") if path.exists() else
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<labwc_config><keyboard><default /></keyboard></labwc_config>\n')
    root = ET.fromstring(text)
    if root.tag != "labwc_config":
        raise ValueError("Unexpected Labwc configuration root.")

    if MARKED.search(text):
        # Keep current managed region, including any deliberate user edits.
        return "already-installed"

    # Refuse to steal explicitly defined mouse gestures, including Alt+Left.
    # The default bindings are not represented here unless a user configured
    # them, so these checks preserve customized configurations.
    for context in root.findall("./mouse/context"):
        if (context.get("name") or "").casefold() != "frame":
            continue
        for binding in context.findall("mousebind"):
            button = (binding.get("button") or "").casefold()
            if button in ("w-left", "a-left"):
                return "skip-custom-mousebind"

    if re.search(r"</mouse\s*>", text):
        updated = re.sub(r"</mouse\s*>", lambda _: "  " + BLOCK + "\n</mouse>",
                         text, count=1)
    elif re.search(r"</labwc_config\s*>", text):
        updated = re.sub(
            r"</labwc_config\s*>",
            lambda _: "  <mouse>\n    <default />\n    " + BLOCK +
                      "\n  </mouse>\n</labwc_config>",
            text, count=1)
    else:
        raise ValueError("Labwc rc.xml lacks a closing root element.")
    ET.fromstring(updated)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".rc-tres-drag-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(updated)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return "installed"
