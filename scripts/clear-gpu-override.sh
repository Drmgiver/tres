#!/usr/bin/env bash
set -euo pipefail
rm -f -- "$HOME/.config/tres-labwc/drm-device"
echo 'Removed Tres GPU preference. Next Tres login uses the compositor default.'
