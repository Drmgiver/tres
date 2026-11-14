#!/usr/bin/env bash
# Build a Tres source upload for an explicitly supported Ubuntu PPA series.
# Without --unsigned the source changes and DSC are signed locally with GPG.
set -euo pipefail

usage() {
  echo "Usage: $0 <noble|resolute> [--unsigned]" >&2
  exit 2
}

[[ ${1:-} == noble || ${1:-} == resolute ]] || usage
series=$1
mode=${2:-}
[[ -z $mode || $mode == --unsigned ]] || usage

case "$series" in
  noble) ubuntu_version=24.04 ;;
  resolute) ubuntu_version=26.04 ;;
esac
version="1.0.0-1~ppa1~ubuntu${ubuntu_version}.1"
key="2914B44A8F9A39641D18E89873D67A036AAA0D36"
root=$(git rev-parse --show-toplevel)
cd "$root"

# Package committed Git content only: no local configuration, .git, or
# potentially modified/untracked files accidentally enter public uploads.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Working tree contains uncommitted changes. Commit or stash them first." >&2
  exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/tres-1.0.0"
git archive --format=tar HEAD | tar -xf - -C "$tmp/tres-1.0.0"

# The Debian changelog stays 'unstable' in Git. Ubuntu-targeted entries
# exist only in the temporary source package, never in the source repo.
changelog="$tmp/tres-1.0.0/debian/changelog"
{
  printf 'tres (%s) %s; urgency=medium\n\n' "$version" "$series"
  printf '  * Publish Tres 1.0 Gold to the %s Ubuntu PPA series.\n\n' "$series"
  printf ' -- J. Michael Willenburg <drmgiver@gmail.com>  %s\n\n' "$(date -R)"
  cat "$changelog"
} > "$tmp/changelog.new"
mv "$tmp/changelog.new" "$changelog"

# A 3.0 (quilt) source package requires an orig tarball containing upstream
# files, but not the debian/ packaging directory.
tar -C "$tmp" --exclude='tres-1.0.0/debian' -czf "$tmp/tres_1.0.0.orig.tar.gz" tres-1.0.0

cd "$tmp/tres-1.0.0"
if [[ $mode == --unsigned ]]; then
  dpkg-buildpackage -S -sa --no-sign
else
  gpg --list-secret-keys "$key" >/dev/null || {
    echo "The Tres signing key is not available in this GPG keyring." >&2
    exit 1
  }
  dpkg-buildpackage -S -sa -k"$key"
fi

output="$root/dist/ppa/$series"
mkdir -p "$output"
cp "$tmp/tres_1.0.0.orig.tar.gz" "$output/"
cp "$tmp/tres_${version}.dsc" "$tmp/tres_${version}.debian.tar."* "$tmp/tres_${version}_source.changes" "$output/"
echo "Source upload prepared: $output/tres_${version}_source.changes"
if [[ $mode == --unsigned ]]; then
  echo "UNSIGNED review artifact only; this cannot be uploaded to Launchpad."
else
  echo "Upload with: dput ppa:drmgiver/tres '$output/tres_${version}_source.changes'"
fi
