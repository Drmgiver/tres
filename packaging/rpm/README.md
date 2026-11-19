# Tres on Open Build Service — experimental RPM

This directory contains a **prototype RPM** for openSUSE and Fedora, not a
tested or released package. The existing Debian/Ubuntu PPA is unaffected.

## OBS project and source

Target project: [home:Drmgiver](https://build.opensuse.org/project/show/home:Drmgiver).
Create a package named `tres` and add these files to its source page:

- `packaging/rpm/tres.spec` (upload as **tres.spec**)
- `packaging/rpm/_service` (upload as **_service**)

The OBS `obs_scm` service fetches source from the Tres GitHub repository
and creates `tres-1.0.1.tar.xz` at build time. **During development only**,
it tracks `main`. Pin the revision to an immutable release tag (and update
`Version`) before publishing real binaries. Do not mix this experimental
version with the frozen PPA 1.0.0 upstream archive.

The RPM recipe copies the same Python modules and package-managed launchers
used by Debian, but has its own RPM-compatible session bootstrap. It does
not run `apt`, `dnf`, or `zypper` in the build or installation scripts.
Package dependencies are resolved by OBS/RPM.

## Initial builds (not installation)

1. Add an **openSUSE Tumbleweed x86_64** repository target in
   your OBS home project's **Repositories** tab.
2. Upload `tres.spec` and `_service` to the OBS `tres` package.
3. Review OBS **Build Results** for `unresolvable` missing dependencies
   before attempting to install the RPM.
4. Once Tumbleweed builds cleanly, add Fedora x86_64 as a separate
   target and address distribution-specific dependencies.
5. Test the resulting package and the Tres login session on expendable
   test machines or virtual machines before enabling publication.

### Distribution differences

- On openSUSE the GTK3 layer-shell GObject-introspection typelib has the
  package name `typelib-1_0-GtkLayerShell-0_1`.
- On Fedora the `gtk-layer-shell` package includes the typelib.
- `lxpolkit` is recommended rather than mandatory during the initial
  multi-distribution trial; graphical privileged actions need a working
  Polkit agent. Do not claim full desktop integration without testing it.
- Audio controls use `wpctl` or `pactl`; these are intentionally
  not hard runtime dependencies.

**Caution:** The source archive must contain `packaging/rpm/tres-session`
from the merged upstream branch. If the OBS `_service` runs before this
packaging work is merged, the build will fail.

The RPM package must never be installed over a source/script-managed Tres
session without first reviewing ownership and startup configuration.
