#!/usr/bin/env bash
# Update only Tres's installed login wrapper. Avoid rerunning apt-get.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="/usr/local/bin/tres-labwc-session"
if [[ ! -f "$WRAPPER" ]] || ! grep -q '^# A dedicated session' "$WRAPPER"; then
  echo "Refusing to overwrite missing/unrecognized wrapper: $WRAPPER" >&2
  echo 'Run bash install.sh only if Tres is not installed yet.' >&2
  exit 1
fi
sh -n "$ROOT/scripts/tres-session.sh"
sudo install -m 0755 "$ROOT/scripts/tres-session.sh" "$WRAPPER"
echo 'Updated Tres standalone launcher and debugging. COSMIC is unchanged.'
