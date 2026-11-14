"""Tres-only Labwc mouse configuration without swallowing Super+left.

Labwc's Frame context consumes pointer events even for empty bindings. To
deliver Super+left to our GTK layer-shell panel, it must be absent entirely.
Therefore we explicitly materialize the stock non-Super-left mouse bindings
instead of using <mouse><default />, which reinstalls the intercepted event.
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
MOUSE = re.compile(r"<mouse(?:\s+[^>]*)?>.*?</mouse\s*>", re.DOTALL)
MOUSE_DEFAULT = re.compile(r"<default\s*/>")

# Explicit stock Labwc mouse behavior, minus Frame/W-Left.
# Original reference: https://github.com/labwc/labwc/blob/master/docs/rc.xml.all
# Users can still add their own additional contexts after these defaults.
DEFAULT_BINDINGS = {
    "Frame": [
        ("W-Right", "Press", "Focus", "Raise"),
        ("W-Right", "Drag", "Resize"),
    ],
    "Border": [("Left", "Press", "Focus", "Raise"),
               ("Left", "Drag", "Resize")],
    "TitleBar": [("Left", "Press", "Focus", "Raise"),
                 ("Right", "Click", "Focus", "Raise"),
                 ("Up", "Scroll", "Unshade", "Focus"),
                 ("Down", "Scroll", "Unfocus", "Shade")],
    "Title": [("Left", "Drag", "Move"),
              ("Left", "DoubleClick", "ToggleMaximize"),
              ("Right", "Click", "ShowMenu")],
    "Maximize": [("Left", "Click", "ToggleMaximize"),
                 ("Right", "Click", "ToggleMaximize"),
                 ("Middle", "Click", "ToggleMaximize")],
    "WindowMenu": [("Left", "Click", "ShowMenu"),
                   ("Right", "Click", "ShowMenu")],
    "Icon": [("Left", "Click", "ShowMenu"),
             ("Right", "Click", "ShowMenu")],
    "Shade": [("Left", "Click", "ToggleShade")],
    "AllDesktops": [("Left", "Click", "ToggleOmnipresent")],
    "Iconify": [("Left", "Click", "Iconify")],
    "Close": [("Left", "Click", "Close")],
    "Client": [("Left", "Press", "Focus", "Raise"),
               ("Middle", "Press", "Focus", "Raise"),
               ("Right", "Press", "Focus", "Raise")],
    "Root": [("Left", "Press", "ShowMenu"),
             ("Right", "Press", "ShowMenu"),
             ("Middle", "Press", "ShowMenu"),
             ("Up", "Scroll", "GoToDesktop"),
             ("Down", "Scroll", "GoToDesktop")],
}


def default_xml() -> str:
    """Keep standard window, decoration and desktop mouse gestures intact."""
    lines = ["<!-- BEGIN TRES DEFAULT MOUSE WITHOUT SUPER-LEFT -->"]
    for context, bindings in DEFAULT_BINDINGS.items():
        lines.append(f'<context name="{context}">')
        for button, event, *actions in bindings:
            attr = "direction" if event == "Scroll" else "button"
            lines.append(f'<mousebind {attr}="{button}" action="{event}">')
            for action in actions:
                attrs = ""
                if action == "ShowMenu":
                    attrs = (' menu="root-menu"' if context == "Root"
                             else ' menu="client-menu"')
                elif action == "GoToDesktop":
                    attrs = ' to="left" wrap="yes"' if button == "Up" else ' to="right" wrap="yes"'
                elif action == "ToggleMaximize" and context == "Maximize":
                    attrs = (' direction="horizontal"' if button == "Right" else
                             ' direction="vertical"' if button == "Middle" else "")
                if action == "ShowMenu" and context in ("WindowMenu", "Icon"):
                    attrs += ' atCursor="no"'
                lines.append(f'<action name="{action}"{attrs} />')
            lines.append("</mousebind>")
        lines.append("</context>")
    lines.append("<!-- END TRES DEFAULT MOUSE WITHOUT SUPER-LEFT -->")
    return "\n".join(lines)


# No Frame Super+left binding here: even an empty binding consumes the event.
ALT_DRAG = """<!-- BEGIN TRES PANEL DRAG -->
<context name="Frame">
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

    mouse = root.find("mouse")
    current_managed = MARKED.search(text) is not None
    # Idempotent after migration: an explicitly expanded default block
    # is already present, and no Frame Super binding is reintroduced.
    if "BEGIN TRES DEFAULT MOUSE WITHOUT SUPER-LEFT" in text:
        return "already-installed"
    # Do not silently replace a fully hand-written mouse configuration
    # without <default />; the user may rely on its explicit ordering.
    if mouse is not None and mouse.find("default") is None:
        return "skip-custom-mouse-config"
    for context in root.findall("./mouse/context"):
        if (context.get("name") or "").casefold() != "frame":
            continue
        for binding in context.findall("mousebind"):
            button = (binding.get("button") or "").casefold()
            # Ignore previous Tres-managed entries but protect independent
            # user overrides that appear outside our marked block.
            if button in ("w-left", "a-left") and not current_managed:
                return "skip-custom-mousebind"

    if mouse is not None:
        match = MOUSE.search(text)
        if match is None:
            raise ValueError("Could not locate mouse configuration.")
        body = match.group(0)
        if current_managed:
            body = MARKED.sub("", body)
        # Remove the defaults in the mouse section ONLY, leaving the
        # keyboard <default/> and all other sections untouched.
        if not MOUSE_DEFAULT.search(body):
            return "skip-custom-mouse-config"
        body = MOUSE_DEFAULT.sub(lambda _: default_xml(), body, count=1)
        body = re.sub(r"</mouse\s*>", lambda _: ALT_DRAG + "\n</mouse>", body, count=1)
        updated = text[:match.start()] + body + text[match.end():]
    else:
        mouse_content = "<mouse>\n" + default_xml() + "\n" + ALT_DRAG + "\n</mouse>"
        updated = re.sub(r"</labwc_config\s*>",
                         lambda _: mouse_content + "\n</labwc_config>",
                         text, count=1)
        if updated == text:
            raise ValueError("Labwc configuration has no closing root.")
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
    return "upgraded" if current_managed else "installed"
