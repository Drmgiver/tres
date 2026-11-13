#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${WAYLAND_DISPLAY:-}" ]]; then
    echo 'Log into your regular COSMIC Wayland session to run this test.' >&2
    exit 1
fi
if ! command -v labwc >/dev/null 2>&1; then
    echo 'Labwc is missing. Run bash install.sh first.' >&2
    exit 1
fi
echo 'Starting Labwc nested in a window. Use Alt+F4 to close the nested session.'
WLR_BACKENDS=wayland WLR_WL_OUTPUTS=1 labwc -C "$HOME/.config/tres/labwc"
