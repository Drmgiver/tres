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
