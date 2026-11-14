# Debian / Ubuntu packaging for Tres

This directory contains a **candidate** Debian source package and a GitHub
Actions workflow for building an installable `.deb`. Packaging does not
automatically get the software into Debian or Ubuntu archives.

## Build on GitHub

Open the [Debian package workflow](../.github/workflows/debian-package.yml) in this repository.
Select a successful run and download the `tres-debian-packages` artifact.
The ZIP contains `tres_1.0.0-1_all.deb`, an **unsigned** source package
for review, and a lintian report. It is **not yet an official Ubuntu package**.

The `Architecture: all` Debian package installs an optional
`Tres` login session, and depends on the existing distribution
packages Labwc, GTK3 layer-shell bindings, `wlrctl`, Python GI, `foot`,
and `swaybg`.

To test a build on an apt-based Linux system **on a spare/test machine first**:

```bash
sudo apt install ./tres_1.0.0-1_all.deb
```

Choose **Tres** at the login screen. Keep your current desktop
environment installed. To remove the package:

```bash
sudo apt remove tres
```

Do **not** run the former shell-installation `uninstall.sh` against a
package-managed Tres session. Use `sudo apt remove tres` to uninstall
the new package.

### Migrating an existing Tres-Labwc installation

The previous project installed configuration under
`~/.config/tres-labwc/` and provided an optional Debian package named
`tres-labwc`. This release uses `~/.config/tres/`, a package named
`tres`, and a login choice labelled **Tres**.

**Before** installing the new package (or at least before first signing in),
run the migration script from your source checkout:

```bash
bash scripts/migrate-legacy.sh
```

It copies the old configuration if the new directory does not already
exist, retains your display scaling/GPU settings, and never removes the
original. If the new directory already exists, the helper refuses to merge
the two so nothing is silently overwritten.

Alternatively, after installing the .deb, the package's first-run
session wrapper can perform that safe copy automatically when no new
configuration exists.

The Debian control file declares **Breaks/Replaces** for the old
`tres-labwc` package. APT may remove the old experimental package when
installing `tres`. Keep your old source checkout and another
desktop session available until you have tested the renamed Tres session.

**Legacy shell installers:** the renamed project installs a new login
entry at `/usr/share/wayland-sessions/tres.desktop`; it deliberately
does not delete the old `tres-labwc.desktop` entry during migration.
You can clean up the old entry only after confirming the new session works.

### Local builds

With Debian packaging build dependencies installed:

```bash
sudo apt install debhelper dh-python dpkg-dev lintian
dpkg-buildpackage --build=binary --no-sign
```

The build emits `../tres_1.0.0-1_all.deb`.
For a **source** package, create an upstream source tarball first (without
the `debian` directory), then build source:

```bash
srcdir="$(basename "$PWD")"
cd ..
tar --exclude-vcs --exclude="$srcdir/debian" \
    --transform="s|^$srcdir|tres-1.0.0|" \
    -czf tres_1.0.0.orig.tar.gz "$srcdir"
cd "$srcdir"
dpkg-buildpackage --build=source --no-sign
```

An upload to the Debian mentors or Ubuntu archive must have the proper
signatures and other checks; the unsigned CI artifacts are for review/testing.

## Tres 1.0 Gold — Launchpad PPA upload

Tres's official PPA is https://launchpad.net/~drmgiver/+archive/ubuntu/tres.
The GitHub release remains the upstream source. Launchpad imports its code
separately and does not publish installable packages until a source upload.

**Build signed source uploads on the maintainer's Linux computer** with the
registered OpenPGP secret key available. Never upload a private key to GitHub
Actions or Launchpad. The CI workflow builds *unsigned review artifacts only*.

Install the necessary Debian/Ubuntu packaging tools:

```bash
sudo apt update
sudo apt install build-essential debhelper dh-python dpkg-dev devscripts dput lintian python3
```

Update the local source checkout, then build **one Ubuntu series at a time**:

```bash
cd ~/Tres
git pull --ff-only
bash scripts/build-ppa-source.sh noble
```

The script checks that the Git working tree is clean, snapshots committed Git
files, constructs the `tres_1.0.0.orig.tar.gz` upstream tarball, inserts a
temporary Ubuntu-specific changelog entry, and creates a GPG-signed source
upload at `dist/ppa/noble/`. It does *not* alter `debian/changelog` in Git.
To send that signed Ubuntu 24.04 source package to the PPA:

```bash
dput ppa:drmgiver/tres dist/ppa/noble/tres_1.0.0-1~ppa1~ubuntu24.04.1_source.changes
```

For Ubuntu 26.04, reuse the **exact** upstream source archive already
accepted for Noble. The build script reads
`dist/ppa/noble/tres_1.0.0.orig.tar.gz`, unpacks that immutable upstream
source, and adds the Ubuntu-specific Debian changelog/packaging. Do not
regenerate the original archive from newer Git commits: Launchpad rejects
different contents under the same upstream archive filename.

```bash
bash scripts/build-ppa-source.sh resolute
dput -f ppa:drmgiver/tres dist/ppa/resolute/tres_1.0.0-1~ppa1~ubuntu26.04.1_source.changes
```

For Ubuntu 26.10 (Stonking Stingray), use that *same* immutable source
archive and build a separate release-specific upload:

```bash
bash scripts/build-ppa-source.sh stonking
dput ppa:drmgiver/tres dist/ppa/stonking/tres_1.0.0-1~ppa1~ubuntu26.10.1_source.changes
```

For Ubuntu 27.04 (Tenacious T-Rex; **development release until April 2027**),
prepare and sign a separate package without rebuilding the upstream archive.
There is no need to wait for 26.10's Launchpad build to finish:

```bash
cd ~/Tres
git pull --ff-only
bash scripts/build-ppa-source.sh tenacious
dput ppa:drmgiver/tres dist/ppa/tenacious/tres_1.0.0-1~ppa1~ubuntu27.04.1_source.changes
```

Check Launchpad acceptance, build result, and publication. Treat Tenacious
as pre-release support until tested against the final April 2027 release.
This does not upload the immutable upstream source archive again.

The original source archive from Noble must remain in
`dist/ppa/noble/tres_1.0.0.orig.tar.gz` for the signed upload to work.
Launchpad builds the 26.10 binary separately. Verify acceptance, build
success, and publication in Launchpad before announcing support.

The `-f` upload option handles a local `dput` record left by a prior
rejected attempt. New signed source changes reference the original archive
without reuploading it. **Keep the Noble original source archive**; if it is
missing, restore the identical one from the first accepted PPA upload, not
a newly compressed Git snapshot.


Each version is unique to its Ubuntu release. Do not upload unsigned CI
artifacts; Launchpad accepts source uploads signed by a registered key.
Check accepted uploads and build results at the PPA URL; a successful local
source build is not proof that the PPA has published installable packages.

After successful publication on an Ubuntu release for which this PPA provides
packages:

```bash
sudo add-apt-repository ppa:drmgiver/tres
sudo apt update
sudo apt install tres
```

Keep another desktop session installed while testing Tres.

## Debian Mentors upload (ITP #1153994)

Debian's Intent to Package is filed as
[WNPP #1153994](https://bugs.debian.org/1153994).
The package's Debian source version is `1.0.0-1`, targeted to `unstable`.
**Do not submit the Ubuntu PPA source upload to Debian Mentors.**

The initial Debian upload uses the **same original upstream 1.0.0 source
archive** already used for Noble PPA publication. The script copies the
current `debian/` packaging into a temporary build directory and prepares
a separate source-only upload. It does not modify the current Git checkout
or replace the user's installed Tres session.

Install Debian packaging and upload tools on the maintainer's Linux laptop:

```bash
sudo apt update
sudo apt install build-essential debhelper dh-python dpkg-dev devscripts dput lintian
```

After confirming the current `debian/` package passes GitHub's
**Debian unstable package review** workflow:

```bash
cd ~/Tres
git pull --ff-only
bash scripts/build-debian-source.sh
```

The script requires the existing **exact** original tarball at
`~/Tres/dist/ppa/noble/tres_1.0.0.orig.tar.gz`, and the maintainer's local
OpenPGP signing key. It creates signed source files in `dist/debian/`,
including `tres_1.0.0-1_source.changes`. The user's GPG private key stays
on their own laptop. Never upload that private key.

Before the first upload, ensure the Debian Mentors account has the
**matching public signing key**, and add this HTTPS upload stanza to
`~/.dput.cf` **without replacing existing unrelated entries**:

```ini
[mentors]
fqdn = mentors.debian.net
incoming = /upload
method = https
allow_unsigned_uploads = 0
progress_indicator = 2
allowed_distributions = .*
```

Then, **after reviewing the signed package**:

```bash
cd ~/Tres
dput mentors dist/debian/tres_1.0.0-1_source.changes
```

Wait for the Debian Mentors import confirmation and verify the Tres entry
on your Mentors account/package page. A successful `dput` only confirms
transfer, not Debian archive acceptance. The Mentors site then provides
the RFS template for the next step. Official instructions:
https://mentors.debian.net/intro-maintainers/.

### Upstream release tracking

The initial 1.0.0 upstream archive was frozen for the Noble PPA before
GitHub release tags existed. The current `main` source is not identical
to that original archive, so a retroactive `v1.0.0` tag on current
`main` would be misleading.

There is currently **no `debian/watch` file**, because no discoverable
upstream release tags or download assets exist for `uscan` to track.
The missing watch-file informational notice is preferable to a false
nonfunctional tracker. After publishing the next genuine upstream
release with an immutable version tag, introduce a Debian watch-format-5
GitHub template and verify it using `uscan --no-download --verbose`.

## Getting into Debian and Ubuntu

**For public availability now: publish the PPA first, then submit to Debian.**

1. Confirm the package name is available, select an actual, reachable
   maintainer email address, verify the GPL copyright notices and release
   version, and run a clean build/lintian check. The maintainer is
   J. Michael Willenburg <drmgiver@gmail.com>.
2. File an Intent to Package (ITP) in Debian's WNPP bug tracker.
3. Build the source package in a Debian unstable/sid clean environment
   (prefer `sbuild`), sign it with the maintainer's OpenPGP key, and
   upload it to [mentors.debian.net](https://mentors.debian.net/).
4. File a Request For Sponsorship (RFS), respond to review feedback, and
   find a Debian Developer to upload the package.
5. Once accepted in Debian unstable, Ubuntu normally imports/syncs
   Debian packages before Debian Import Freeze. After the freeze, a sync
   request may be needed.

**Ubuntu-specific alternative:** file an Ubuntu Launchpad bug tagged
`needs-packaging`, link the upstream project and Debian ITP/RFP if there
is one, and request sponsorship from `ubuntu-sponsors`. Ubuntu's default
archive is reviewed and an upload requires developer sponsorship.

For users who want packages before official acceptance, a **Launchpad PPA**
can build and distribute the source package (with a signed upload). A PPA is
not equivalent to inclusion in the official Ubuntu archive.

Official documentation:

- https://ubuntu.com/project/docs/how-ubuntu-is-made/processes/new-packages/
- https://ubuntu.com/project/docs/contributors/uploading/find-a-sponsor/
- https://mentors.debian.net/intro-maintainers/
- https://ubuntu.com/docs/launchpad/user/how-to/packaging/build-deb-packages-in-launchpad/

## Packaging scope

The Debian package deliberately does **not** install a new default display
manager, replace an existing desktop environment, auto-select a GPU, or configure a screen locker.
The first-run session copies a minimal autostart file into the user's private
Tres configuration if absent. Existing user configuration is left untouched.
