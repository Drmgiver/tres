#!/usr/bin/env bash
# Explicit, opt-in migration for users of Tres's old bash install.sh.
# Run AFTER installing the .deb. Do not run the legacy uninstaller afterwards.
set -euo pipefail
cfg="$HOME/.config/tres-labwc/labwc/autostart"
if [[ ! -f "$cfg" ]]; then
    echo "No legacy autostart found: $cfg"
    exit 0
fi
if ! grep -Fq '"$HOME/.local/bin/tres-panel"' "$cfg"; then
    echo "No legacy panel path found; nothing to migrate."
    exit 0
fi
backup="$cfg.before-deb"
if [[ -e "$backup" ]]; then
    echo "Refusing to overwrite previous backup: $backup" >&2
    exit 1
fi
cp -p -- "$cfg" "$backup"
sed -i 's|"$HOME/.local/bin/tres-panel"|/usr/bin/tres-panel|g' "$cfg"
echo "Switched Tres autostart to /usr/bin/tres-panel"
echo "Original configuration saved as $backup"
echo "The packaged session will take effect after you log out and back in."
