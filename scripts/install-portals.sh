#!/usr/bin/env bash
# Install a desktop-specific portal preference without touching global defaults.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
DEST="${XDG_CONFIG_HOME:-$HOME/.config}/xdg-desktop-portal/tres-portals.conf"
mkdir -p -- "$(dirname -- "$DEST")"
if [[ ! -e "$DEST" && ! -L "$DEST" ]]; then
    install -m 0644 "$ROOT/scripts/tres-portals.conf" "$DEST"
    echo 'Installed Tres portal backend preferences.'
else
    echo 'Kept existing Tres portal preferences.'
fi


# Existing Tres installs retain their autostart. Add D-Bus environment export
# only to recognized Tres autostarts so portal services receive Wayland context.
AUTOSTART="$HOME/.config/tres/labwc/autostart"
if [[ -f "$AUTOSTART" && ! -L "$AUTOSTART" ]] &&
   grep -Fq 'tres-panel' "$AUTOSTART" &&
   ! grep -Fq 'dbus-update-activation-environment' "$AUTOSTART"; then
    if [[ ! -e "$AUTOSTART.before-tres-portals" ]]; then
        cp -p -- "$AUTOSTART" "$AUTOSTART.before-tres-portals"
    fi
    /usr/bin/python3 - "$AUTOSTART" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
old = path.read_text(encoding="utf-8")
block = (
    'if command -v dbus-update-activation-environment >/dev/null 2>&1; then\n'
    '    dbus-update-activation-environment --systemd WAYLAND_DISPLAY '
    'XDG_CURRENT_DESKTOP XDG_SESSION_DESKTOP >/dev/null 2>&1 || true\n'
    'fi\n'
)
if old.startswith("#!") and "dbus-update-activation-environment" not in old:
    pos = old.find("\n") + 1
    path.write_text(old[:pos] + block + old[pos:], encoding="utf-8")
PY
fi
