#!/usr/bin/env bash
# Idempotently install Tres-only launchers without sudo or modifying COSMIC.
set -euo pipefail
BIN="$HOME/.local/bin"
AUTOSTART="$HOME/.config/tres/labwc/autostart"
mkdir -p "$BIN"

if [[ -e "$BIN/tres-open-files" ]] && ! grep -q '^# Tres-managed launcher$' "$BIN/tres-open-files"; then
    echo "Existing unrecognized $BIN/tres-open-files; not overwriting" >&2
else
    cat > "$BIN/tres-open-files" <<'EOF'
#!/bin/sh
# Tres-managed launcher
exec /usr/bin/python3 "$HOME/.local/share/tres/tres_open.py" "$@"
EOF
    chmod 0755 "$BIN/tres-open-files"
fi

if [[ -e "$BIN/tres-wallpaper" ]] && ! grep -q '^# Tres-managed launcher$' "$BIN/tres-wallpaper"; then
    echo "Existing unrecognized $BIN/tres-wallpaper; not overwriting" >&2
else
    cat > "$BIN/tres-wallpaper" <<'EOF'
#!/bin/sh
# Tres-managed launcher
exec /usr/bin/python3 "$HOME/.local/share/tres/tres_wallpaper.py" "$@"
EOF
    chmod 0755 "$BIN/tres-wallpaper"
fi

# Migrate only the known, unmodified legacy swaybg command. Never
# overwrite arbitrary custom wallpaper scripts or the user's scale block.
if [[ -f "$AUTOSTART" ]] &&
   grep -Fq "swaybg -c '#141414'" "$AUTOSTART" &&
   ! grep -Fq 'tres-wallpaper' "$AUTOSTART"; then
    cp -p -- "$AUTOSTART" "$AUTOSTART.before-tres-wallpaper"
    /usr/bin/python3 - "$AUTOSTART" <<'PY'
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
old = path.read_text(encoding="utf-8")
updated = old.replace("swaybg -c '#141414'", '"$HOME/.local/bin/tres-wallpaper"')
if updated != old:
    path.write_text(updated, encoding="utf-8")
    os.chmod(path, path.stat().st_mode | 0o100)
PY
    echo "Upgraded default Tres wallpaper launcher; previous autostart backed up."
fi
