#!/usr/bin/env bash
# Copy old Tres-Labwc user settings into the new Tres namespace.
# Never remove or overwrite the old configuration.
set -euo pipefail
old="$HOME/.config/tres-labwc"
new="$HOME/.config/tres"

if [[ ! -d "$old" ]]; then
    echo 'No previous Tres configuration found; new Tres can use defaults.'
    exit 0
fi
if [[ -e "$new" ]]; then
    echo "Already exists: $new"
    echo 'Keeping both configurations untouched; review and migrate manually if needed.'
    exit 0
fi

cp -a -- "$old" "$new"

# The old shell installer and old Debian package used different
# launchers. Update only the launcher reference in a COPY of autostart.
autostart="$new/labwc/autostart"
if [[ -f "$autostart" ]]; then
    if command -v dpkg-query >/dev/null 2>&1 &&
       dpkg-query -W -f='${Status}' tres 2>/dev/null | grep -q 'install ok installed'; then
        # The package-managed panel lives in /usr/bin.
        sed -i 's|"$HOME/.local/bin/tres-panel"|/usr/bin/tres-panel|g' "$autostart"
    fi
fi

echo "Copied previous Tres settings into $new"
echo 'Old settings were left in place so the previous session still works.'
echo 'Display scale, GPU preference, and other options were preserved.'
