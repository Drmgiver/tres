#!/usr/bin/env bash
# Tres-managed Synaptic launcher: temporary root access to this XWayland display.
set -euo pipefail
if [[ -z "${DISPLAY:-}" ]]; then
    echo "Synaptic requires an XWayland DISPLAY." >&2
    exit 1
fi
for binary in xhost synaptic-pkexec flock; do
    command -v "$binary" >/dev/null 2>&1 || {
        echo "Synaptic launcher requires $binary." >&2
        exit 1
    }
done
runtime="${XDG_RUNTIME_DIR:-$HOME/.cache/tres}"
mkdir -p "$runtime"
# Serialize permission toggling across launches from Tres.
exec 9>"$runtime/tres-synaptic-xhost.lock"
flock -x 9
# Respect an authorization rule that the user or another application already set.
had_access=0
if xhost 2>/dev/null | grep -Eq '(^|[[:space:]])SI:localuser:root([[:space:]]|$)'; then
    had_access=1
fi
granted=0
cleanup() {
    if [[ "$granted" == 1 ]]; then
        xhost -si:localuser:root >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
if [[ "$had_access" == 0 ]]; then
    xhost +si:localuser:root >/dev/null || exit 1
    granted=1
fi
# Keep this process alive until Synaptic/pkexec exits, then restore X access.
synaptic-pkexec "$@"
