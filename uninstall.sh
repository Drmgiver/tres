#!/usr/bin/env bash
set -euo pipefail
SESSION=/usr/share/wayland-sessions/tres.desktop
WRAPPER=/usr/local/bin/tres-session
if command -v dpkg-query >/dev/null 2>&1 && dpkg-query -S "$SESSION" >/dev/null 2>&1; then
    echo 'Tres is managed by dpkg. Remove it with: sudo apt remove tres' >&2
    exit 1
fi
if [[ -f "$SESSION" ]] && grep -q '^X-Tres=true$' "$SESSION"; then
    sudo rm -f -- "$SESSION"
fi
if [[ -f "$WRAPPER" ]] && grep -q '^# A dedicated session' "$WRAPPER"; then
    sudo rm -f -- "$WRAPPER"
fi
rm -rf -- "$HOME/.local/share/tres"
rm -f -- "$HOME/.local/bin/tres-panel"
echo "Removed Tres panel and login entry."
echo "Left user configuration in ~/.config/tres/ for safekeeping."
echo "Other desktop sessions and apt-installed packages have not been changed."
