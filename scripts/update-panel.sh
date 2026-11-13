#!/usr/bin/env bash
# Copy updated Tres panel code from a git checkout; no sudo or apt needed.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$HOME/.local/share/tres"
BIN="$HOME/.local/bin"
CFG="$HOME/.config/tres/labwc"

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
for name in ("tres_core.py", "tres_panel.py", "tres_layout.py", "tres_config.py", "tres_capture.py", "tres_screenshot.py"):
    ast.parse((src / name).read_text(encoding="utf-8"), filename=name)
print("Python source syntax: OK")
PY

install -m 0644 "$ROOT/src/tres_core.py" "$DEST/tres_core.py"
install -m 0644 "$ROOT/src/tres_panel.py" "$DEST/tres_panel.py"
install -m 0644 "$ROOT/src/tres_layout.py" "$DEST/tres_layout.py"
install -m 0644 "$ROOT/src/tres_config.py" "$DEST/tres_config.py"
install -m 0644 "$ROOT/src/tres_capture.py" "$DEST/tres_capture.py"
install -m 0644 "$ROOT/src/tres_screenshot.py" "$DEST/tres_screenshot.py"
bash "$ROOT/scripts/install-screenshot.sh"
mkdir -p "$BIN" "$CFG"
cat > "$BIN/tres-config" <<'EOF'
#!/bin/sh
# Tres stacking configuration launcher.
exec /usr/bin/python3 "$HOME/.local/share/tres/tres_config.py" "$@"
EOF
chmod 0755 "$BIN/tres-config"
if [[ ! -e "$CFG/menu.xml" ]]; then
    install -m 0644 "$ROOT/scripts/menu.xml" "$CFG/menu.xml"
    echo "Installed Reconfigure Tres in the desktop right-click menu."
    if [[ -n "${WAYLAND_DISPLAY:-}" ]] && command -v labwc >/dev/null 2>&1; then
        labwc --reconfigure >/dev/null 2>&1 || true
    fi
else
    echo "Keeping existing $CFG/menu.xml (add Reconfigure Tres manually if customized)"
fi
echo "Tres panel updated. Close any running nested Labwc window,"
echo "then log out and back into Tres to activate the new stacking options."
