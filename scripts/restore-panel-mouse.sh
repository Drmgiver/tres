#!/usr/bin/env bash
# One-time cleanup of the abandoned Tres panel-drag experiment.
# Restores Labwc's built-in mouse defaults while preserving user bindings.
set -euo pipefail
RC="${XDG_CONFIG_HOME:-$HOME/.config}/tres/labwc/rc.xml"
/usr/bin/python3 - "$RC" <<'PY'
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

p = Path(sys.argv[1])
if not p.is_file() or p.is_symlink():
    sys.exit(0)
old = p.read_text(encoding="utf-8")
default_block = re.compile(
    r"<!-- BEGIN TRES DEFAULT MOUSE WITHOUT SUPER-LEFT -->.*?"
    r"<!-- END TRES DEFAULT MOUSE WITHOUT SUPER-LEFT -->",
    re.S,
)
drag_block = re.compile(
    r"<!-- BEGIN TRES PANEL DRAG -->.*?<!-- END TRES PANEL DRAG -->",
    re.S,
)
if not default_block.search(old) and not drag_block.search(old):
    sys.exit(0)
# Never replace an invalid or unexpected configuration.
root = ET.fromstring(old)
if root.tag != "labwc_config":
    raise ValueError("Unexpected Labwc configuration; mouse settings unchanged")
mouse = root.find("mouse")
if mouse is None:
    sys.exit(0)
updated = default_block.sub("", old)
updated = drag_block.sub("", updated)
# For previously expanded defaults, reintroduce <default /> *only inside
# the mouse section*. Keep all other explicit user mouse binds as-is.
if default_block.search(old):
    start = re.search(r"<mouse(?:\s+[^>]*)?>", updated)
    if start is None:
        raise ValueError("Could not find Labwc mouse section")
    close = updated.find("</mouse>", start.end())
    if close < 0:
        raise ValueError("Could not find end of Labwc mouse section")
    body = updated[start.end():close]
    if not re.search(r"<default\s*/>", body):
        updated = updated[:start.end()] + "\n    <default />" + updated[start.end():]
ET.fromstring(updated)
if updated == old:
    sys.exit(0)
fd, tmp = tempfile.mkstemp(prefix=".rc-tres-mouse-restore-", dir=p.parent)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(updated)
    os.chmod(tmp, p.stat().st_mode & 0o777)
    os.replace(tmp, p)
finally:
    if os.path.exists(tmp):
        os.unlink(tmp)
print("Tres: removed experimental mouse bindings; Labwc defaults restored.")
PY
# A previously enabled debug switch no longer serves any purpose.
rm -f -- "$HOME/.config/tres/trace-panel-drag"
