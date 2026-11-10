#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/tres-labwc"
BIN="$HOME/.local/bin"
CFG="$HOME/.config/tres-labwc/labwc"
SESSION=/usr/share/wayland-sessions/tres-labwc.desktop
SYSTEM_WRAPPER=/usr/local/bin/tres-labwc-session

if [[ ${EUID} -eq 0 ]]; then
    echo 'Run this script as your normal desktop user, not root.' >&2
    exit 1
fi
if ! command -v apt-get >/dev/null 2>&1; then
    echo 'This installer targets Ubuntu/Pop!_OS apt systems. See README for manual setup.' >&2
    exit 1
fi
if [[ -e "$SESSION" ]] && ! grep -q '^X-Tres-Labwc=true$' "$SESSION"; then
    echo "Refusing to replace unknown existing session: $SESSION" >&2
    exit 1
fi
if [[ -e "$SYSTEM_WRAPPER" ]] && ! grep -q '^# A dedicated session' "$SYSTEM_WRAPPER"; then
    echo "Refusing to replace unknown launcher: $SYSTEM_WRAPPER" >&2
    exit 1
fi

printf '%s\n' 'Installing Labwc, GTK3 layer-shell, wlrctl, a terminal, and wallpaper helper.'
sudo apt-get update
sudo apt-get install -y labwc python3-gi gir1.2-gtk-3.0 gir1.2-gtklayershell-0.1 wlrctl foot swaybg

mkdir -p "$DEST" "$BIN" "$CFG"
install -m 0644 "$ROOT/src/tres_core.py" "$DEST/tres_core.py"
install -m 0644 "$ROOT/src/tres_panel.py" "$DEST/tres_panel.py"
cat > "$BIN/tres-panel" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 "$HOME/.local/share/tres-labwc/tres_panel.py" "$@"
EOF
chmod 0755 "$BIN/tres-panel"
if [[ ! -e "$CFG/autostart" ]]; then
    install -m 0755 "$ROOT/scripts/autostart" "$CFG/autostart"
else
    echo "Keeping existing $CFG/autostart"
fi

sudo install -m 0755 "$ROOT/scripts/tres-session.sh" "$SYSTEM_WRAPPER"
tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT
cat > "$tmpfile" <<'EOF'
[Desktop Entry]
Name=Tres (Labwc)
Comment=Three-square minimalist Wayland desktop
Exec=/usr/local/bin/tres-labwc-session
TryExec=/usr/bin/labwc
Type=Application
DesktopNames=labwc
X-Tres-Labwc=true
EOF
sudo install -m 0644 "$tmpfile" "$SESSION"

echo
echo 'Installed. Log out, then choose "Tres (Labwc)" at the login screen.'
echo 'Your COSMIC session was not altered. Test first; avoid unsaved work.'
echo 'To test nested inside COSMIC: bash scripts/test-nested.sh'
