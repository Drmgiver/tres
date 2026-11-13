#!/usr/bin/env bash
# Read-only diagnostic for Tres/Labwc standalone session failures.
set -uo pipefail

echo '=== Tres / Labwc diagnostics ==='
echo "Current desktop: ${XDG_CURRENT_DESKTOP:-unknown}"
echo "Current session: ${XDG_SESSION_TYPE:-unknown}"
echo
echo '=== Graphics devices and drivers ==='
if command -v lspci >/dev/null 2>&1; then
  lspci -nnk | grep -Ei -A 4 'VGA compatible controller|3D controller|Display controller' || true
else
  echo 'lspci not installed'
fi
echo
echo '=== Labwc / rendering messages from current and previous boots ==='
echo 'Look at the section covering your failed Tres login (usually boot -1 if you rebooted).'
echo 'If the journal is access-restricted, rerun the script with sudo -E for read-only system logs.'
for boot in 0 -1; do
  echo
  echo "--- boot $boot ---"
  logs="$(journalctl -b "$boot" --no-pager -o short-iso 2>&1)"
  if [[ $? -ne 0 ]] || [[ "$logs" == *"No journal files were found"* ]]; then
    echo 'Journal for this boot unavailable.'
    continue
  fi
  matches="$(printf '%s\n' "$logs" | grep -Ei 'labwc|wlroots|libseat|seatd|gbm|egl|renderer|drm|nvidia|amdgpu|segfault|GPU reset' | tail -n 100)"
  if [[ -n "$matches" ]]; then
    printf '%s\n' "$matches"
  else
    echo 'No matching entries (or journal access is restricted).'
  fi
done
echo
echo '=== Tres panel log, if any ==='
if [[ -f "${HOME}/.cache/tres-labwc/panel.log" ]]; then
  tail -n 25 "${HOME}/.cache/tres-labwc/panel.log"
else
  echo 'No panel log. Labwc may have failed before autostart.'
fi
echo
echo 'NOTE: Review output before sharing; journal entries may include machine names and paths.'
