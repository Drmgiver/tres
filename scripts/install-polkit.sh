#!/usr/bin/env bash
# Integrate graphical authentication into Tres only, preserving custom startup.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$HOME/.local/bin"
AUTOSTART="$HOME/.config/tres/labwc/autostart"
mkdir -p "$BIN" "$(dirname "$AUTOSTART")"
target="$BIN/tres-polkit-agent"
if [[ -L "$target" ]] || { [[ -e "$target" ]] && ! grep -qx '# Tres-managed Polkit authentication agent starter.' "$target" 2>/dev/null; }; then
    echo "Refusing to overwrite unrelated launcher: $target" >&2
    exit 1
fi
install -m 0755 "$ROOT/scripts/tres-polkit-agent.sh" "$target"
if [[ ! -e "$AUTOSTART" ]]; then
    install -m 0755 "$ROOT/scripts/autostart" "$AUTOSTART"
fi
if [[ -L "$AUTOSTART" ]]; then
    echo "Tres autostart is a symlink; add tres-polkit-agent manually." >&2
    exit 1
fi
if ! grep -Fq 'tres-polkit-agent' "$AUTOSTART"; then
    cat >> "$AUTOSTART" <<'EOF'

# Tres graphical administrator authentication
"$HOME/.local/bin/tres-polkit-agent" >> "$HOME/.cache/tres/polkit.log" 2>&1 &
EOF
fi
if ! command -v lxpolkit >/dev/null 2>&1; then
    echo "Missing lxpolkit: run sudo apt-get install lxpolkit" >&2
fi
echo "Tres Polkit agent configured; log out and back into Tres."
