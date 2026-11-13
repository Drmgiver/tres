#!/usr/bin/env bash
# Set Labwc Wayland output scale now, and keep it on subsequent Tres logins.
set -euo pipefail

if [[ "$#" -ne 2 ]]; then
    echo 'Usage: bash scripts/set-scale.sh OUTPUT SCALE' >&2
    echo 'Example: bash scripts/set-scale.sh eDP-1 1.5' >&2
    echo 'Run wlr-randr to discover your output name.' >&2
    exit 2
fi
output="$1"
scale="$2"

if ! command -v wlr-randr >/dev/null 2>&1; then
    echo 'wlr-randr is missing. Install with: sudo apt install wlr-randr' >&2
    exit 1
fi
if ! [[ "$scale" =~ ^[0-9]+([.][0-9]+)?$ ]] ||
    ! awk -v x="$scale" 'BEGIN {exit !(x >= 0.75 && x <= 3.0)}'; then
    echo 'Scale must be a number between 0.75 and 3 (for example: 1.25, 1.5, 2).' >&2
    exit 2
fi
if [[ "$output" == -* || "$output" == "" ]]; then
    echo 'Invalid output name. Run wlr-randr to find the actual display.' >&2
    exit 2
fi

# Fail before persisting anything if the compositor rejects the setting.
wlr-randr --output "$output" --scale "$scale"

config="$HOME/.config/tres/labwc"
mkdir -p -- "$config"
python3 - "$config/autostart" "$output" "$scale" <<'PY'
from pathlib import Path
import re
import shlex
import sys

path = Path(sys.argv[1])
output = shlex.quote(sys.argv[2])
scale = shlex.quote(sys.argv[3])
begin = "# BEGIN TRES DISPLAY SCALE"
end = "# END TRES DISPLAY SCALE"
old = path.read_text(encoding="utf-8") if path.exists() else "#!/bin/sh\n"
# Remove only the script's clearly marked block.
pattern = re.compile(r"(?m)^# BEGIN TRES DISPLAY SCALE\n.*?^# END TRES DISPLAY SCALE\n?", re.S)
new = pattern.sub("", old).rstrip("\n")
block = f"""\n{begin}
# Output name is from wlr-randr; runs only inside this Tres session.
(sleep 1; wlr-randr --output {output} --scale {scale}) >/dev/null 2>&1 &
{end}
"""
path.write_text(new + "\n" + block, encoding="utf-8")
path.chmod(path.stat().st_mode | 0o100)
PY

echo "Applied scale $scale to $output and saved it for future Tres sessions."
echo "Other desktop environments' display settings were not changed."
