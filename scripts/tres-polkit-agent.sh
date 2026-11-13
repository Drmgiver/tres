#!/bin/sh
# Tres-managed Polkit authentication agent starter.
# Run only inside Tres, never alter other desktop sessions.
case ":${XDG_CURRENT_DESKTOP:-}:" in
    *:tres:*|*:Tres:*) ;;
    *) exit 0 ;;
esac
if ! command -v lxpolkit >/dev/null 2>&1; then
    printf '%s\n' 'Tres: lxpolkit is missing; install the lxpolkit package.' >&2
    exit 1
fi
# Avoid a second copy when the session already started the agent.
if command -v pgrep >/dev/null 2>&1 &&
   pgrep -u "$(id -u)" -x lxpolkit >/dev/null 2>&1; then
    exit 0
fi
exec lxpolkit
