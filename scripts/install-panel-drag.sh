#!/usr/bin/env bash
# Configure only Tres's own Labwc compositor; leave other desktops untouched.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MODULE_DIR="${TRES_MODULE_DIR:-$ROOT/src}"
RC="$HOME/.config/tres/labwc/rc.xml"

/usr/bin/python3 - "$MODULE_DIR" "$RC" <<'PY'
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, sys.argv[1])
from tres_mouse import configure

try:
    state = configure(Path(sys.argv[2]))
except (ValueError, OSError, ET.ParseError) as error:
    print(f"Tres drag: keeping existing mouse config: {error}")
else:
    if state == "installed":
        print("Tres drag: Super+left reserved for panel; Alt+left moves ordinary windows.")
    elif state == "skip-custom-mousebind":
        print("Tres drag: existing custom Super/Alt mouse bindings preserved; "
              "automatic setup skipped.")
    elif state == "skip-symlink":
        print("Tres drag: symlinked Labwc rc.xml preserved; automatic setup skipped.")
PY
