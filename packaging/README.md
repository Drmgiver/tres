# Debian / Ubuntu packaging for Tres

This directory contains a **candidate** Debian source package and a GitHub
Actions workflow for building an installable `.deb`. Packaging does not
automatically get the software into Debian or Ubuntu archives.

## Build on GitHub

Open [Debian package workflow](https://github.com/Drmgiver/tres-labwc/actions/workflows/debian-package.yml).
Select a successful run and download the `tres-labwc-debian-packages` artifact.
The ZIP contains `tres-labwc_0.1.0-1_all.deb`, an **unsigned** source package
for review, and a lintian report. It is **not yet an official Ubuntu package**.

The `Architecture: all` Debian package installs an optional
`Tres (Labwc)` login session, and depends on the existing distribution
packages Labwc, GTK3 layer-shell bindings, `wlrctl`, Python GI, `foot`,
and `swaybg`.

To test a build on Ubuntu/Pop!_OS **on a spare/test machine first**:

```bash
sudo apt install ./tres-labwc_0.1.0-1_all.deb
```

Choose **Tres (Labwc)** at the login screen. Keep your current desktop
environment installed. To remove the package:

```bash
sudo apt remove tres-labwc
```

Do **not** run the old `uninstall.sh` after installing the Debian package:
the old uninstaller removes a session entry now owned by dpkg.

### Migrating an existing Tres installation

The original `install.sh` wrote a user autostart file that launches the
panel from `~/.local/bin/tres-panel`, while the Debian package uses
`/usr/bin/tres-panel`. The Debian package won't replace your user
configuration automatically. After installing the package, run:

```bash
bash packaging/deb/migrate-legacy.sh
```

The migration script backs up your original autostart file, changes **only**
the old panel-launcher path, and preserves your saved scaling commands.
Log out and sign back into Tres to use the package-managed implementation.
Keep the original files until you've confirmed the packaged session works.

### Local builds

With Debian packaging build dependencies installed:

```bash
sudo apt install debhelper dh-python dpkg-dev lintian
dpkg-buildpackage --build=binary --no-sign
```

The build emits `../tres-labwc_0.1.0-1_all.deb`.
For a **source** package, create an upstream source tarball first (without
the `debian` directory), then build source:

```bash
cd ..
tar --exclude='tres-labwc/.git' --exclude='tres-labwc/debian' \
    -czf tres-labwc_0.1.0.orig.tar.gz tres-labwc
cd tres-labwc
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
manager, replace COSMIC/GNOME, auto-select a GPU, or configure a screen locker.
The first-run session copies a minimal autostart file into the user's private
Tres configuration if absent. Existing user configuration is left untouched.
