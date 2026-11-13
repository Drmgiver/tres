#!/usr/bin/env bash
# Copy updated Tres panel code from a git checkout; no sudo or apt needed.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$HOME/.local/share/tres"

if [[ ! -d "$DEST" ]]; then
    echo 'Tres is not installed yet. Run bash install.sh once.' >&2
    exit 1
fi

# Validate syntax before touching the installed files.
/usr/bin/python3 - "$ROOT" <<'PY'
import ast
from pathlib import Path
import sys
src = Path(sys.argv[1]) / "src"
for name in ("tres_core.py", "tres_panel.py"):
    ast.parse((src / name).read_text(encoding="utf-8"), filename=name)
print("Python source syntax: OK")
PY

install -m 0644 "$ROOT/src/tres_core.py" "$DEST/tres_core.py"
install -m 0644 "$ROOT/src/tres_panel.py" "$DEST/tres_panel.py"
echo "Tres panel updated. Close any running nested Labwc window,"
echo "then run: bash scripts/test-nested.sh"
