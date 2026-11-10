#!/bin/sh
# A dedicated session; never modifies or replaces Pop!_OS's COSMIC session.
export XDG_SESSION_TYPE=wayland
export XDG_CURRENT_DESKTOP=labwc
export XDG_SESSION_DESKTOP=tres-labwc
exec /usr/bin/labwc -C "$HOME/.config/tres-labwc/labwc"
