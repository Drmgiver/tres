#!/usr/bin/env bash
# Install panel recovery without overwriting custom autostart/menu entries.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
BIN="$HOME/.local/bin"
CFG="$HOME/.config/tres/labwc"
mkdir -p "$BIN" "$CFG"
# These are Tres-owned launchers; never clobber an unrelated executable.
for launcher in tres-panel-supervisor tres-panel-control; do
    target="$BIN/$launcher"
    if [[ -L "$target" ]] ||
       { [[ -e "$target" ]] &&
         ! grep -qx '# Tres-managed launcher' "$target" 2>/dev/null; }; then
        echo "Refusing to replace unrecognized launcher: $target" >&2
        exit 1
    fi
done
install -m 0755 "$ROOT/scripts/tres-panel-supervisor.sh" "$BIN/tres-panel-supervisor"
cat > "$BIN/tres-panel-control" <<'EOF'
#!/bin/sh
# Tres-managed launcher
exec /usr/bin/python3 "$HOME/.local/share/tres/tres_panel_control.py" "$@"
EOF
chmod 0755 "$BIN/tres-panel-control"

AUTOSTART="$CFG/autostart"
if [[ -f "$AUTOSTART" && ! -L "$AUTOSTART" ]] &&
   grep -Fq '"$HOME/.local/bin/tres-panel" >> "$HOME/.cache/tres/panel.log" 2>&1 &' "$AUTOSTART" &&
   ! grep -Fq 'tres-panel-supervisor' "$AUTOSTART"; then
    if [[ ! -e "$AUTOSTART.before-tres-supervisor" ]]; then
        cp -p -- "$AUTOSTART" "$AUTOSTART.before-tres-supervisor"
    fi
    /usr/bin/python3 - "$AUTOSTART" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
old = p.read_text(encoding="utf-8")
new = old.replace(
    '"$HOME/.local/bin/tres-panel" >> "$HOME/.cache/tres/panel.log" 2>&1 &',
    '"$HOME/.local/bin/tres-panel-supervisor" >/dev/null 2>&1 &',
)
if new != old:
    p.write_text(new, encoding="utf-8")
PY
fi
/usr/bin/python3 - "$ROOT/src" "$CFG/menu.xml" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from tres_menu import add_restart_action
add_restart_action(
    Path(sys.argv[2]),
    str(Path.home() / ".local/bin/tres-panel-control") + " restart",
)
PY
