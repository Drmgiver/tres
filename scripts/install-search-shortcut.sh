#!/usr/bin/env bash
# Install the new search shortcut once, preserving existing keybindings.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MODULE_DIR="${TRES_MODULE_DIR:-$ROOT/src}"
/usr/bin/python3 - "$MODULE_DIR" "$HOME/.config/tres/labwc/rc.xml" "$HOME/.config/tres/search-shortcut-initialized" <<'PY'
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from tres_shortcuts import read_shortcuts, save_shortcuts

rc = Path(sys.argv[2])
stamp = Path(sys.argv[3])
if stamp.exists():
    sys.exit(0)
if rc.is_symlink():
    print("Tres: custom symlinked keyboard configuration; configure Search manually.")
    sys.exit(0)
keys = read_shortcuts(rc)
if keys.get("search"):
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.touch(mode=0o600, exist_ok=True)
    sys.exit(0)
try:
    if rc.exists():
        root = ET.parse(rc).getroot()
        # Do not steal Super+Space from an unrelated Labwc binding.
        if any((node.get("key") or "").casefold() == "w-space"
               for node in root.iter("keybind")):
            print("Tres: Super+Space already in use; configure Search in Keyboard settings.")
            sys.exit(0)
    keys["search"] = "W-space"
    save_shortcuts(keys, rc)
except (OSError, ValueError, ET.ParseError) as error:
    print(f"Tres: could not initialize search shortcut: {error}")
    sys.exit(0)
stamp.parent.mkdir(parents=True, exist_ok=True)
stamp.touch(mode=0o600, exist_ok=True)
print("Tres: Super+Space now opens Search Applications.")
PY
