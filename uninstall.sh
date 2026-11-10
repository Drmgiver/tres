#!/usr/bin/env bash
set -euo pipefail
SESSION=/usr/share/wayland-sessions/tres-labwc.desktop
WRAPPER=/usr/local/bin/tres-labwc-session
if [[ -f "$SESSION" ]] && grep -q '^X-Tres-Labwc=true$' "$SESSION"; then
    sudo rm -f -- "$SESSION"
fi
if [[ -f "$WRAPPER" ]] && grep -q '^# A dedicated session' "$WRAPPER"; then
    sudo rm -f -- "$WRAPPER"
fi
rm -rf -- "$HOME/.local/share/tres-labwc"
rm -f -- "$HOME/.local/bin/tres-panel"
echo "Removed Tres panel and login entry."
echo "Left user configuration in ~/.config/tres-labwc/ for safekeeping."
echo "COSMIC and the apt-installed packages have not been changed."
