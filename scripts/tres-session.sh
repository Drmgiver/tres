#!/bin/sh
# Tres-managed session launcher
# A standalone session that does not modify other desktop environments.
export XDG_SESSION_TYPE=wayland
export XDG_CURRENT_DESKTOP=tres:labwc:wlroots
export XDG_SESSION_DESKTOP=tres

# Keep the compositor's own errors across a failed graphical login. The panel
# log alone cannot diagnose failures before the first output is ready.
logdir="$HOME/.cache/tres"
mkdir -p "$logdir" || exit 1
chmod 700 "$logdir" || exit 1
umask 077
log="$logdir/labwc-standalone.log"
{
    printf '\n=== Tres standalone start: %s ===\n' "$(date -Is)"
    printf 'Session type: %s\n' "$XDG_SESSION_TYPE"
} >> "$log"

# Optional, reversible graphics preference. A normal installation has no
# override. Only a plain /dev/dri/cardN device is accepted; no shell code is
# ever evaluated from user-supplied configuration.
choice_file="$HOME/.config/tres/drm-device"
if [ -r "$choice_file" ]; then
    IFS= read -r candidate < "$choice_file" || true
    resolved="$(readlink -f "$candidate" 2>/dev/null || true)"
    case "$resolved" in
        /dev/dri/card[0-9]*)
            if [ -e "$resolved" ]; then
                export WLR_DRM_DEVICES="$resolved"
                printf 'Using selected DRM device: %s\n' "$resolved" >> "$log"
            else
                printf 'Selected DRM device is missing: %s\n' "$candidate" >> "$log"
            fi
            ;;
        *)
            printf 'Invalid DRM device override (ignored): %s\n' "$candidate" >> "$log"
            ;;
    esac
fi

# Avoid stale compositor display variables when launching a real login session.
unset WAYLAND_DISPLAY WAYLAND_SOCKET DISPLAY

# -d is Labwc's supported verbose debug option. Redirect both streams so
# another black screen leaves a useful record after reboot.
exec /usr/bin/labwc -d -C "$HOME/.config/tres/labwc" >> "$log" 2>&1
