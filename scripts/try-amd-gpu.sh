#!/usr/bin/env bash
# Opt in to the AMD GPU only for the Tres standalone login. This does not
# modify Pop!_OS, NVIDIA drivers, COSMIC, or any global GPU configuration.
set -euo pipefail
pci="0000:65:00.0"
path="/dev/dri/by-path/pci-${pci}-card"
if [[ ! -e "$path" ]]; then
  echo "AMD DRM symlink not found: $path" >&2
  echo 'Available DRM paths:' >&2
  ls -l /dev/dri/by-path/ 2>&1 >&2 || true
  exit 1
fi
real="$(readlink -f "$path")"
device="${real##*/}"
driver_link="/sys/class/drm/$device/device/driver"
driver="$(basename "$(readlink -f "$driver_link")")"
if [[ "$driver" != "amdgpu" ]]; then
  echo "Refusing selection: $path is using driver '$driver', not amdgpu" >&2
  exit 1
fi
mkdir -p "$HOME/.config/tres-labwc"
printf '%s\n' "$path" > "$HOME/.config/tres-labwc/drm-device"
echo "Tres standalone GPU override set to $path ($driver)"
echo 'The setting applies only at the next Tres login.'
echo 'Undo: bash scripts/clear-gpu-override.sh'
