#!/usr/bin/env bash
# Build a Tres source upload for an explicitly supported Ubuntu PPA series.
# Without --unsigned the source changes and DSC are signed locally with GPG.
set -euo pipefail

usage() {
  echo "Usage: $0 <noble|resolute|stonking|tenacious> [--unsigned]" >&2
  exit 2
}

[[ ${1:-} == noble || ${1:-} == resolute || ${1:-} == stonking || ${1:-} == tenacious ]] || usage
series=$1
mode=${2:-}
[[ -z $mode || $mode == --unsigned ]] || usage

case "$series" in
  noble) ubuntu_version=24.04 ;;
  resolute) ubuntu_version=26.04 ;;
  stonking) ubuntu_version=26.10 ;;
  tenacious) ubuntu_version=27.04 ;;
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
# Upstream source archives are immutable across Ubuntu series. Noble was
# accepted first, so its exact .orig.tar.gz is the canonical Tres 1.0 source.
# Never regenerate a different tarball under the same upstream version.
canonical_orig="$root/dist/ppa/noble/tres_1.0.0.orig.tar.gz"
if [[ -f $canonical_orig ]]; then
  cp "$canonical_orig" "$tmp/tres_1.0.0.orig.tar.gz"
  tar -xzf "$tmp/tres_1.0.0.orig.tar.gz" -C "$tmp"
  test -d "$tmp/tres-1.0.0" || {
    echo "Unexpected directory structure in the canonical Tres 1.0 tarball." >&2
    exit 1
  }
  include_orig=no
elif [[ $mode == --unsigned && $series == noble ]]; then
  # CI-only bootstrap of a sample orig archive. Its content is NOT guaranteed
  # to match the one already accepted by Launchpad.
  mkdir -p "$tmp/tres-1.0.0"
  git archive --format=tar HEAD | tar -xf - -C "$tmp/tres-1.0.0"
  tar -C "$tmp" --exclude='tres-1.0.0/debian' -czf "$tmp/tres_1.0.0.orig.tar.gz" tres-1.0.0
  include_orig=yes
else
  echo "Missing the original Tres 1.0 source archive:" >&2
  echo "  $canonical_orig" >&2
  echo "Do not regenerate it from the current Git checkout." >&2
  echo "Restore the exact noble archive from your first accepted upload." >&2
  exit 1
fi

# Packaging metadata can evolve, but the upstream content must come from
# that frozen original tarball, not a newer HEAD revision.
rm -rf "$tmp/tres-1.0.0/debian"
cp -a "$root/debian" "$tmp/tres-1.0.0/debian"

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

# The initial CI test includes the orig tarball. Subsequent signed uploads
# reference the archive already in Launchpad, without re-uploading it.
cd "$tmp/tres-1.0.0"
source_include_flag=-sd
if [[ $include_orig == yes ]]; then source_include_flag=-sa; fi
if [[ $mode == --unsigned ]]; then
  dpkg-buildpackage -S "$source_include_flag" --no-sign
else
  gpg --list-secret-keys "$key" >/dev/null || {
    echo "The Tres signing key is not available in this GPG keyring." >&2
    exit 1
  }
  dpkg-buildpackage -S "$source_include_flag" -k"$key"
fi

output="$root/dist/ppa/$series"
mkdir -p "$output"
cp "$tmp/tres_1.0.0.orig.tar.gz" "$output/"
cp "$tmp/tres_${version}.dsc" "$tmp/tres_${version}.debian.tar."* "$tmp/tres_${version}_source.changes" "$tmp/tres_${version}_source.buildinfo" "$output/"
# Fail before suggesting upload if any artifact referenced by .changes is missing.
for artifact in $(awk '/^Files:/{inside=1;next} inside && /^[^ ]/{exit} inside && /^ / {print $5}' "$output/tres_${version}_source.changes"); do
  test -s "$output/$artifact" || { echo "Missing source upload artifact: $artifact" >&2; exit 1; }
done
echo "Source upload prepared: $output/tres_${version}_source.changes"
if [[ $mode == --unsigned ]]; then
  echo "UNSIGNED review artifact only; this cannot be uploaded to Launchpad."
else
  echo "Upload with: dput ppa:drmgiver/tres '$output/tres_${version}_source.changes'"
fi
