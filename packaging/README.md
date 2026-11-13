# Debian / Ubuntu packaging for Tres

This directory contains a **candidate** Debian source package and a GitHub
Actions workflow for building an installable `.deb`. Packaging does not
automatically get the software into Debian or Ubuntu archives.

## Build on GitHub

Open the [Debian package workflow](../.github/workflows/debian-package.yml) in this repository.
Select a successful run and download the `tres-debian-packages` artifact.
The ZIP contains `tres_0.5.5-1_all.deb`, an **unsigned** source package
for review, and a lintian report. It is **not yet an official Ubuntu package**.

The `Architecture: all` Debian package installs an optional
`Tres` login session, and depends on the existing distribution
packages Labwc, GTK3 layer-shell bindings, `wlrctl`, Python GI, `foot`,
and `swaybg`.

To test a build on an apt-based Linux system **on a spare/test machine first**:

```bash
sudo apt install ./tres_0.5.5-1_all.deb
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

The build emits `../tres_0.5.5-1_all.deb`.
For a **source** package, create an upstream source tarball first (without
the `debian` directory), then build source:

```bash
srcdir="$(basename "$PWD")"
cd ..
tar --exclude-vcs --exclude="$srcdir/debian" \
    --transform="s|^$srcdir|tres-0.5.5|" \
    -czf tres_0.5.5.orig.tar.gz "$srcdir"
cd "$srcdir"
dpkg-buildpackage --build=source --no-sign
```

An upload to the Debian mentors or Ubuntu archive must have the proper
signatures and other checks; the unsigned CI artifacts are for review/testing.

## Getting into Debian and Ubuntu

**Preferred route: Debian first.**

1. Confirm the package name is available, select an actual, reachable
   maintainer email address, verify the GPL copyright notices and release
   version, and run a clean build/lintian check. The current GitHub
   `users.noreply` address is **provisional** and must be replaced before
   applying for maintainership/sponsorship.
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
