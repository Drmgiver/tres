#!/usr/bin/env bash
# Register a user-local Screenshot app without changing other desktop tools.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
mkdir -p -- "$BIN" "$APPS"

cat > "$BIN/tres-screenshot" <<'EOF'
#!/bin/sh
# Tres-managed launcher
exec /usr/bin/python3 "$HOME/.local/share/tres/tres_screenshot.py" "$@"
EOF
chmod 0755 "$BIN/tres-screenshot"

desktop="$APPS/tres-screenshot.desktop"
if [[ -e "$desktop" ]] &&
   ! grep -qx 'X-Tres-Screenshot=true' "$desktop"; then
    echo "Keeping unrecognized launcher $desktop; Tres Screenshot executable is installed." >&2
    exit 0
fi

/usr/bin/python3 - "$ROOT/scripts/tres-screenshot.desktop" "$desktop" "$BIN/tres-screenshot" <<'PY'
from pathlib import Path
import sys

template = Path(sys.argv[1]).read_text(encoding="utf-8")
destination = Path(sys.argv[2])
executable = sys.argv[3]
# Exec paths with spaces must be quoted according to Desktop Entry syntax.
escaped = executable.replace("\\", "\\\\").replace('"', '\\"')
text = template.replace("Exec=tres-screenshot", 'Exec="' + escaped + '"')
if text == template:
    raise SystemExit("Screenshot launcher template is missing Exec=tres-screenshot")
destination.write_text(text, encoding="utf-8")
PY
echo 'Tres Screenshot added to Accessories.'
