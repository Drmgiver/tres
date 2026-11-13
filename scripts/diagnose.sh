#!/usr/bin/env bash
set -u
printf 'Wayland session: %s\n' "${XDG_SESSION_TYPE:-unknown}"
printf 'Compositor: %s\n' "${XDG_CURRENT_DESKTOP:-unknown}"
for cmd in labwc wlrctl foot swaybg /usr/bin/python3; do
    if command -v "$cmd" >/dev/null 2>&1; then printf '[yes] %s\n' "$cmd";
    else printf '[no]  %s\n' "$cmd"; fi
done
/usr/bin/python3 - <<'PY'
try:
    import gi
    gi.require_version('Gdk', '3.0')
    gi.require_version('Gtk', '3.0')
    gi.require_version('GtkLayerShell', '0.1')
    from gi.repository import Gdk, Gio, Gtk, GtkLayerShell
    print('[yes] Python GTK3 and GTK layer-shell')
except Exception as exc:
    print('[no]  GTK3 layer-shell:', exc)
PY
printf '\nFor errors inspect: ~/.cache/tres/panel.log\n'
# Do NOT print window titles: they may contain private material.
