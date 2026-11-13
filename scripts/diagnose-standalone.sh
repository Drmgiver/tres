#!/usr/bin/env bash
# Read-only diagnostic for Tres/Labwc standalone session failures.
set -uo pipefail

echo '=== Tres diagnostics ==='
echo "Current desktop: ${XDG_CURRENT_DESKTOP:-unknown}"
echo "Current session: ${XDG_SESSION_TYPE:-unknown}"
echo
echo '=== Graphics devices and drivers ==='
if command -v lspci >/dev/null 2>&1; then
  lspci -nnk 2>/dev/null | grep -Ei -A 4 'VGA compatible controller|3D controller|Display controller' || true
else
  echo 'lspci not installed'
fi
echo
echo '=== DRM card symlinks and active connectors ==='
ls -l /dev/dri/by-path/*-card 2>/dev/null || true
for status in /sys/class/drm/card*-*/status; do
  [[ -f "$status" ]] || continue
  printf '%s: %s\n' "${status%/status}" "$(cat "$status" 2>/dev/null)"
done
echo
echo '=== Standalone Labwc debug log ==='
if [[ -f "$HOME/.cache/tres/labwc-standalone.log" ]]; then
  tail -n 120 "$HOME/.cache/tres/labwc-standalone.log"
else
  echo 'No standalone debug log yet (new launcher must be installed and used once).'
fi
echo
echo '=== Relevant journal lines, current and previous boot ==='
echo 'If the journal is access-restricted, rerun with sudo -E for read-only system logs.'
for boot in 0 -1; do
  echo "--- boot $boot ---"
  logs="$(journalctl -b "$boot" --no-pager -o short-iso 2>&1)" || {
    echo 'Journal for this boot unavailable.'
    continue
  }
  matches="$(printf '%s\n' "$logs" | grep -Ei 'labwc|gdm-wayland-session|\[backend/drm/|Failed to parse EDID|libseat|failed to become drm master|\[nvidia-drm\].*ERROR|GPU reset|segfault' | tail -n 70)"
  if [[ -n "$matches" ]]; then
    printf '%s\n' "$matches"
  else
    echo 'No matching lines.'
  fi
done
echo
echo '=== Recent Tres panel warnings ==='
if [[ -f "$HOME/.cache/tres/panel.log" ]]; then
  tail -n 20 "$HOME/.cache/tres/panel.log"
else
  echo 'No panel log.'
fi
echo
echo 'NOTE: Review output before sharing; logs may contain machine names or paths.'
