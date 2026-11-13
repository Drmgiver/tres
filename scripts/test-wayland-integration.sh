#!/usr/bin/env bash
# Real compositor/GTK3 layer-shell smoke test (virtual wlroots output).
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
TMP="$(mktemp -d)"
LABWC_PID=
PANEL_PID=
cleanup() {
    if [[ -n "$PANEL_PID" ]]; then
        kill "$PANEL_PID" 2>/dev/null || true
        wait "$PANEL_PID" 2>/dev/null || true
    fi
    if [[ -n "$LABWC_PID" ]]; then
        kill "$LABWC_PID" 2>/dev/null || true
        wait "$LABWC_PID" 2>/dev/null || true
    fi
    if [[ -f "$TMP/labwc.log" ]]; then
        cat "$TMP/labwc.log"
    fi
    rm -rf -- "$TMP"
}
trap cleanup EXIT

export XDG_RUNTIME_DIR="$TMP/runtime"
mkdir -p "$XDG_RUNTIME_DIR" "$TMP/config"
chmod 0700 "$XDG_RUNTIME_DIR"
export WAYLAND_DISPLAY=tres-test-wl
export WLR_BACKENDS=headless
export WLR_RENDERER=pixman
export WLR_HEADLESS_OUTPUTS=1
export XDG_CURRENT_DESKTOP=tres:labwc:wlroots
export XDG_SESSION_TYPE=wayland

# Prevent recursively launching the full desktop during a smoke test.
printf '#!/bin/sh\n' > "$TMP/config/autostart"
printf '<openbox_menu><menu id="root-menu" label=""/></openbox_menu>\n' > "$TMP/config/menu.xml"
labwc -C "$TMP/config" > "$TMP/labwc.log" 2>&1 &
LABWC_PID=$!

ready=false
for _ in $(seq 1 50); do
    if [[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]]; then
        ready=true
        break
    fi
    kill -0 "$LABWC_PID" 2>/dev/null || break
    sleep 0.2
done
if [[ "$ready" != true ]]; then
    echo 'Labwc did not create a Wayland socket.' >&2
    exit 1
fi

# Exercise the real Wayland output control path without modifying scale.
wlr-randr > "$TMP/outputs.txt"
/usr/bin/python3 - "$ROOT/src" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from tres_display import output_info
assert output_info(), "No enabled Wayland outputs"
PY

# Exercise actual GTK layer-shell initialization, not only AST/unit tests.
PYTHONPATH="$ROOT/src" /usr/bin/python3 "$ROOT/src/tres_panel.py" \
    > "$TMP/panel.log" 2>&1 &
PANEL_PID=$!
sleep 2
if ! kill -0 "$PANEL_PID" 2>/dev/null; then
    echo 'Tres panel exited during real Wayland startup.' >&2
    cat "$TMP/panel.log" >&2
    exit 1
fi

TRES_SETTINGS_SMOKE=1 PYTHONPATH="$ROOT/src" /usr/bin/python3 \
    "$ROOT/src/tres_config.py"
echo 'Headless Wayland integration test passed.'
