#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/tres"
BIN="$HOME/.local/bin"
CFG="$HOME/.config/tres/labwc"
SESSION=/usr/share/wayland-sessions/tres.desktop
SYSTEM_WRAPPER=/usr/local/bin/tres-session

if [[ ${EUID} -eq 0 ]]; then
    echo 'Run this script as your normal desktop user, not root.' >&2
    exit 1
fi
if ! command -v apt-get >/dev/null 2>&1; then
    echo 'This installer targets apt-based Linux systems. See README for manual setup.' >&2
    exit 1
fi
# Do not let the source installer overwrite a package-managed session.
if command -v dpkg-query >/dev/null 2>&1; then
    for owned in "$SESSION" "$SYSTEM_WRAPPER"; do
        if dpkg-query -S "$owned" >/dev/null 2>&1; then
            echo "Package manager owns $owned; use the package updater instead." >&2
            exit 1
        fi
    done
fi
if [[ -e "$SESSION" ]] && ! grep -qx 'X-Tres=true' "$SESSION"; then
    echo "Refusing to replace unknown existing session: $SESSION" >&2
    exit 1
fi
if [[ -e "$SYSTEM_WRAPPER" ]] &&
   ! grep -Eq '^# (Tres-managed session launcher|A standalone session|A dedicated session)' "$SYSTEM_WRAPPER"; then
    echo "Refusing to replace unknown launcher: $SYSTEM_WRAPPER" >&2
    exit 1
fi

printf '%s\n' 'Installing Labwc, GTK3 layer-shell, wlrctl, a terminal, and wallpaper helper.'
sudo apt-get update
sudo apt-get install -y labwc python3-gi gir1.2-gtk-3.0 gir1.2-gtklayershell-0.1 wlrctl foot swaybg grim slurp wlr-randr xdg-desktop-portal xdg-desktop-portal-gtk xdg-desktop-portal-wlr lxpolkit

# Copy the previous Tres configuration, if any, without deleting the old one.
if [[ -d "$HOME/.config/tres-labwc" && ! -e "$HOME/.config/tres" ]]; then
    bash "$ROOT/scripts/migrate-legacy.sh"
fi

mkdir -p "$DEST" "$BIN" "$CFG"
install -m 0644 "$ROOT/src/tres_core.py" "$DEST/tres_core.py"
install -m 0644 "$ROOT/src/tres_panel.py" "$DEST/tres_panel.py"
install -m 0644 "$ROOT/src/tres_layout.py" "$DEST/tres_layout.py"
install -m 0644 "$ROOT/src/tres_config.py" "$DEST/tres_config.py"
install -m 0644 "$ROOT/src/tres_capture.py" "$DEST/tres_capture.py"
install -m 0644 "$ROOT/src/tres_screenshot.py" "$DEST/tres_screenshot.py"
for module in tres_preferences tres_display tres_shortcuts tres_open tres_wallpaper tres_terminal tres_audio tres_panel_control tres_menu tres_applications tres_search tres_position; do
    install -m 0644 "$ROOT/src/$module.py" "$DEST/$module.py"
done
bash "$ROOT/scripts/install-screenshot.sh"
bash "$ROOT/scripts/install-settings.sh"
bash "$ROOT/scripts/install-search-shortcut.sh"
bash "$ROOT/scripts/install-portals.sh"
cat > "$BIN/tres-panel" <<'EOF'
#!/bin/sh
# Tres-managed launcher
exec /usr/bin/python3 "$HOME/.local/share/tres/tres_panel.py" "$@"
EOF
chmod 0755 "$BIN/tres-panel"
cat > "$BIN/tres-config" <<'EOF'
#!/bin/sh
# Tres-managed launcher
# Tres stacking configuration launcher.
exec /usr/bin/python3 "$HOME/.local/share/tres/tres_config.py" "$@"
EOF
chmod 0755 "$BIN/tres-config"
if [[ ! -e "$CFG/menu.xml" ]]; then
    install -m 0644 "$ROOT/scripts/menu.xml" "$CFG/menu.xml"
else
    echo "Keeping existing $CFG/menu.xml (add Reconfigure Tres manually if customized)"
fi
if [[ ! -e "$CFG/autostart" ]]; then
    install -m 0755 "$ROOT/scripts/autostart" "$CFG/autostart"
else
    echo "Keeping existing $CFG/autostart"
fi

bash "$ROOT/scripts/install-panel-recovery.sh"
bash "$ROOT/scripts/install-polkit.sh"

sudo install -m 0755 "$ROOT/scripts/tres-session.sh" "$SYSTEM_WRAPPER"
tmpfile="$(mktemp)"
trap 'rm -f "$tmpfile"' EXIT
cat > "$tmpfile" <<'EOF'
[Desktop Entry]
Name=Tres
Comment=Three-square minimalist Wayland desktop
Exec=/usr/local/bin/tres-session
TryExec=/usr/bin/labwc
Type=Application
DesktopNames=labwc
X-Tres=true
EOF
sudo install -m 0644 "$tmpfile" "$SESSION"

echo
echo 'Installed. Log out, then choose "Tres" at the login screen.'
echo 'Other desktop sessions were not altered. Test first; avoid unsaved work.'
echo 'To test nested inside an existing Wayland desktop: bash scripts/test-nested.sh'
