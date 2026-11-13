#!/bin/sh
# Keep the three-square panel available while its Wayland compositor exists.
set -u
umask 077
runtime="${XDG_RUNTIME_DIR:-$HOME/.cache/tres}"
mkdir -p "$runtime" "$HOME/.cache/tres" || exit 1
pidfile="$runtime/tres-panel.pid"
log="$HOME/.cache/tres/panel.log"
if [ -x "$HOME/.local/bin/tres-panel" ]; then
    panel="$HOME/.local/bin/tres-panel"
else
    panel="/usr/bin/tres-panel"
fi
case "${WAYLAND_DISPLAY:-}" in
    /*) socket="$WAYLAND_DISPLAY" ;;
    "") echo "Tres panel supervisor: no Wayland display." >&2; exit 1 ;;
    *) socket="$runtime/$WAYLAND_DISPLAY" ;;
esac
child=
cleanup() {
    trap - EXIT INT TERM
    if [ -n "$child" ]; then
        kill "$child" 2>/dev/null || true
        wait "$child" 2>/dev/null || true
    fi
    rm -f -- "$pidfile"
}
trap 'exit 0' INT TERM
trap cleanup EXIT
while [ -S "$socket" ]; do
    "$panel" >> "$log" 2>&1 &
    child=$!
    printf '%s\n' "$child" > "$pidfile"
    wait "$child" 2>/dev/null || true
    child=
    rm -f -- "$pidfile"
    [ -S "$socket" ] || break
    sleep 2
done
