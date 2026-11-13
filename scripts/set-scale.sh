#!/usr/bin/env bash
# Apply and persist one output scale without erasing other configured outputs.
set -euo pipefail
if [[ "$#" -ne 2 ]]; then
    echo "Usage: bash scripts/set-scale.sh OUTPUT SCALE" >&2
    exit 2
fi
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
/usr/bin/python3 - "$ROOT/src" "$1" "$2" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from tres_display import DisplayError, apply_scale

try:
    apply_scale(sys.argv[2], float(sys.argv[3]))
except (ValueError, DisplayError, OSError) as error:
    sys.exit(f"Tres scale: {error}")
print(f"Applied scale {sys.argv[3]} to {sys.argv[2]} without changing other outputs.")
PY
