#!/usr/bin/env bash
# Remove only recognizable Tres-owned launchers. Preserve user configuration.
set -euo pipefail

SESSION=/usr/share/wayland-sessions/tres.desktop
WRAPPER=/usr/local/bin/tres-session
BIN="$HOME/.local/bin"
APP="$HOME/.local/share/applications/tres-screenshot.desktop"
DEST="$HOME/.local/share/tres"

if command -v dpkg-query >/dev/null 2>&1 &&
   dpkg-query -W -f='${Status}' tres 2>/dev/null | grep -qx 'install ok installed'; then
    echo 'Tres is managed by dpkg. Remove it with: sudo apt remove tres' >&2
    exit 1
fi

if [[ -f "$SESSION" ]] && grep -qx 'X-Tres=true' "$SESSION" &&
   ! dpkg-query -S "$SESSION" >/dev/null 2>&1; then
    sudo rm -- "$SESSION"
fi
if [[ -f "$WRAPPER" ]] &&
   grep -Eq '^# (Tres-managed session launcher|A standalone session|A dedicated session)' "$WRAPPER" &&
   ! dpkg-query -S "$WRAPPER" >/dev/null 2>&1; then
    sudo rm -- "$WRAPPER"
fi

remove_launcher() {
    local name="$1" target="$BIN/$1" module="$2"
    [[ -f "$target" && ! -L "$target" ]] || return 0
    if grep -qx '# Tres-managed launcher' "$target" ||
       { grep -Fq 'exec /usr/bin/python3' "$target" &&
         grep -Fq "/tres/$module.py" "$target"; }; then
        rm -- "$target"
    else
        echo "Kept unrecognized launcher $target" >&2
    fi
}

remove_launcher tres-panel tres_panel
remove_launcher tres-panel-control tres_panel_control
remove_launcher tres-panel-supervisor tres_panel_supervisor
remove_launcher tres-config tres_config
remove_launcher tres-screenshot tres_screenshot
remove_launcher tres-open-files tres_open
remove_launcher tres-open-terminal tres_terminal
remove_launcher tres-wallpaper tres_wallpaper

if [[ -f "$APP" && ! -L "$APP" ]] &&
   grep -qx 'X-Tres-Screenshot=true' "$APP"; then
    rm -- "$APP"
fi

# Avoid deleting unrelated files placed inside the installation directory.
for module in tres_panel tres_core tres_layout tres_config tres_capture \
              tres_screenshot tres_preferences tres_display tres_shortcuts \
              tres_open tres_wallpaper tres_terminal tres_audio tres_panel_control tres_menu; do
    [[ ! -f "$DEST/$module.py" || -L "$DEST/$module.py" ]] ||
        rm -- "$DEST/$module.py"
done
rmdir -- "$DEST" 2>/dev/null || true

echo "Tres launchers and recognized program files removed."
echo "User preferences in ~/.config/tres/ were preserved."
echo "Other desktop sessions and system packages are unchanged."
