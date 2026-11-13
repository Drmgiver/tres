#!/usr/bin/env bash
# Install Tres launchers; do not execute them during installation.
set -euo pipefail
BIN="$HOME/.local/bin"
AUTOSTART="$HOME/.config/tres/labwc/autostart"
mkdir -p "$BIN"

install_launcher() {
    local name="$1" module="$2"
    local target="$BIN/$name"

    # Never replace an unrelated launcher or an unexpected symlink.
    if [[ -L "$target" ]] ||
       { [[ -e "$target" ]] &&
         ! grep -qx '# Tres-managed launcher' "$target" 2>/dev/null; }; then
        echo "Existing unrecognized $target; not overwriting" >&2
        return
    fi

    # Generate the wrapper only. Do NOT execute the wrapper here.
    cat > "$target" <<EOF
#!/bin/sh
# Tres-managed launcher
exec /usr/bin/python3 "\$HOME/.local/share/tres/$module.py" "\$@"
EOF
    chmod 0755 "$target"
}

install_launcher tres-open-files tres_open
install_launcher tres-wallpaper tres_wallpaper
install_launcher tres-open-terminal tres_terminal

# Migrate only the original Tres wallpaper command. Keep custom commands
# and existing output scaling in the user's private Labwc autostart.
if [[ -f "$AUTOSTART" ]] &&
   grep -Fq "swaybg -c '#141414'" "$AUTOSTART" &&
   ! grep -Fq 'tres-wallpaper' "$AUTOSTART"; then
    if [[ ! -e "$AUTOSTART.before-tres-wallpaper" ]]; then
        cp -p -- "$AUTOSTART" "$AUTOSTART.before-tres-wallpaper"
    fi
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
