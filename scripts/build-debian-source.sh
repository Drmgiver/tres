#!/usr/bin/env bash
# Prepare the initial Tres 1.0.0-1 Debian source upload for mentors.debian.net.
# Never sends a package: the maintainer must review and run dput separately.
set -euo pipefail

usage() {
  echo "Usage: bash scripts/build-debian-source.sh [--unsigned]" >&2
  exit 2
}
mode=${1:-}
[[ -z "$mode" || "$mode" == --unsigned ]] || usage
[[ $# -le 1 ]] || usage

root=$(git rev-parse --show-toplevel)
cd "$root"
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Uncommitted tracked changes detected; commit or stash them before packaging." >&2
  exit 1
fi

version=1.0.0-1
key=2914B44A8F9A39641D18E89873D67A036AAA0D36
orig="$root/dist/ppa/noble/tres_1.0.0.orig.tar.gz"
output="$root/dist/debian"
if [[ ! -f "$orig" ]]; then
  echo "Missing canonical upstream tarball: $orig" >&2
  echo "Use the exact archive from the accepted Noble PPA upload; do not regenerate" >&2
  echo "different Tres 1.0.0 upstream sources under the same version." >&2
  exit 1
fi
if [[ "$mode" != --unsigned ]]; then
  gpg --list-secret-keys "$key" >/dev/null || {
    echo "Tres signing key is missing from this local GPG keyring." >&2
    exit 1
  }
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp "$orig" "$tmp/tres_1.0.0.orig.tar.gz"
tar -xzf "$tmp/tres_1.0.0.orig.tar.gz" -C "$tmp"
test -d "$tmp/tres-1.0.0" || {
  echo "Unexpected top-level directory inside upstream source archive." >&2
  exit 1
}
# Freeze Tres 1.0.0 upstream sources, but use the up-to-date Debian packaging.
rm -rf "$tmp/tres-1.0.0/debian"
cp -a "$root/debian" "$tmp/tres-1.0.0/debian"
grep -q '^tres (1.0.0-1) unstable;' "$tmp/tres-1.0.0/debian/changelog" || {
  echo "Debian changelog is not version 1.0.0-1 for unstable." >&2
  exit 1
}
grep -q 'Closes: #1153994' "$tmp/tres-1.0.0/debian/changelog" || {
  echo "The official ITP #1153994 is missing from debian/changelog." >&2
  exit 1
}

cd "$tmp/tres-1.0.0"
if [[ "$mode" == --unsigned ]]; then
  dpkg-buildpackage -S -sa --no-sign
else
  dpkg-buildpackage -S -sa -k"$key"
fi
mkdir -p "$output"
cp "$tmp/tres_1.0.0.orig.tar.gz" \
  "$tmp/tres_${version}.dsc" \
  "$tmp/tres_${version}.debian.tar."* \
  "$tmp/tres_${version}_source.changes" \
  "$tmp/tres_${version}_source.buildinfo" "$output/"
for artifact in $(awk '/^Files:/{inside=1;next} inside && /^[^ ]/{exit} inside && /^ / {print $5}' "$output/tres_${version}_source.changes"); do
  test -s "$output/$artifact" || {
    echo "The .changes file references a missing upload artifact: $artifact" >&2
    exit 1
  }
done
echo "Debian source package ready: $output/tres_${version}_source.changes"
if [[ "$mode" == --unsigned ]]; then
  echo "This is an UNSIGNED review build. Do not upload to Debian Mentors."
else
  echo "After reviewing the source, run:"
  echo "  dput mentors '$output/tres_${version}_source.changes'"
fi
