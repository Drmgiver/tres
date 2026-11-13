# Tres

A **three-square, ultra-minimal Wayland desktop**, inspired by the old LiteStep
**Tres** theme. This is an original recreation, not original LiteStep theme code.

```
                  [■] [■] [■]
```

Three **blank, 19×19 white squares** centered 3px below the top of the display:

1. **Left:** installed applications, grouped in menus.
2. **Middle:** running windows; select one to activate it.
3. **Right:** clock, battery, audio, network/Bluetooth controls,
   **Reconfigure Tres**, log out, restart, and shut down.

No permanent taskbar, dock, or full-width panel. By default, the three squares
sit above the wallpaper but **below normal windows**, so maximizing a window
covers them completely. Users can choose different stacking behavior.

## Tres Screenshot

Open **Applications → Accessories → Tres Screenshot**. The small GTK3 GUI
supports **Entire screen** and **Select an area** with an optional 0, 3, or
5-second delay, plus a Save As dialog. It uses Grim for capturing and Slurp
for area selection; it does not require a desktop-specific screenshot portal.
Press Escape while selecting an area to return to the dialog.

Tres Screenshot is installed alongside other screenshot utilities without
removing or changing them. It has its own application launcher. The source
installer and update script install that launcher without sudo. The `.deb` includes the application and the Grim/Slurp dependencies.

```bash
cd ~/Tres
git pull --ff-only
bash scripts/update-panel.sh
```

The application menu gets the new launcher on its next opening; logging out
and back in is not normally required for this standalone utility.

## Large application categories

GTK3's long submenu scrolling can stop prematurely on Wayland, hiding
applications at the bottom of a large category. Tres avoids that limitation:
categories with **more than 12 apps** display numbered, alphabetically
ordered sections (**Apps 1–12**, **Apps 13–24**, etc.). Select a section
to see its applications and launch them normally. Smaller categories keep
their existing one-level menu. Very large categories are grouped again
as needed so that no submenu requires scrolling to reach its final entry.
No applications are excluded.

## Display compatibility

Tres detects enabled monitors using the standard text output of `wlr-randr`,
which works with older versions that do not provide a `--json` option. The
Display tab should list your connected output, report its current scale, and
enable **Apply display scale** when an output is selected. Scaling changes
continue to be saved only in Tres's private Labwc autostart configuration.

## Reconfigure Tres

Choose **Reconfigure Tres** from the desktop right-click menu or the rightmost
square. The settings dialog now has four sections:

- **Appearance:** Under / Over / Space reserved; white-square color, hover
  color, square size, and solid-color wallpaper. Your familiar **Under** mode,
  white 19px squares and dark wallpaper remain the defaults. Square changes
  are applied by the running panel, while wallpaper color takes effect after
  the next Tres login. Custom wallpapers are never overwritten.
- **Display:** choose an active Labwc/Wayland output and its scale (75–300%).
  Uses `wlr-randr` and preserves your existing scale block in
  `~/.config/tres/labwc/autostart`, including the original 150% laptop setup.
  Scaling choices are retained independently for each selected monitor.
  Does **not** change another desktop session's settings or monitor resolution.
- **Keyboard:** add or change Screenshot, Open Files and Terminal shortcuts
  using Labwc key notation such as `Print`, `W-e`, and `W-Return`.
  Edits are inserted into a **marked section only** of Tres's private
  `rc.xml`; other custom bindings are preserved. Applies using
  `labwc --reconfigure`. Suggested shortcuts appear as hints until explicitly
  selected and saved; empty fields mean no Tres-specific binding.
- **Default applications:** choose the file manager, browser, email, text
  editor, PDF viewer and Tres's preferred terminal. File and URL defaults
  use the standard XDG MIME system and therefore also affect other Linux
  desktop sessions for the same user; Tres's terminal choice is Tres-only.

The right-square **Files** command launches the file manager you select
under Default applications, using the standard XDG folder association.
The chooser discovers installed graphical file managers from desktop-file
categories **as well as** the normal folder-handler list. It doesn't restrict
choices to a built-in list of executables. If two apps have the same displayed
name, their desktop IDs are shown to distinguish them. A basic fallback is
offered only when the chosen file manager fails and the user agrees.

Only applications with installed desktop entries can appear in the chooser;
terminal-only tools without a desktop entry are not automatically listed.
Changing the file-manager default also changes the user's standard XDG folder
association in other sessions.

The desktop right-click menu also offers **Restart Tres Panel**. A small
supervisor restarts the panel after a crash or a requested restart without
restarting the entire session. The original Labwc **Reconfigure** and **Exit**
commands remain in that menu. The three-square layout remains completely
unchanged unless you explicitly choose different appearance settings.

To update a script-based Tres installation without reinstalling another desktop or
running the full APT installer:

```bash
cd ~/Tres
git pull --ff-only
bash scripts/update-panel.sh
```

Then log out and back into Tres **once** to load the updated panel.
The update script recognizes and migrates old Tres launchers without
replacing custom wallpaper, startup commands, or display scaling. To activate
the updated portal session identity on existing manual installs, run
`bash scripts/update-session.sh` once (requires sudo) and log out and back in.

## Desktop services and audio

Tres uses desktop-scoped XDG portal preferences in
`~/.config/xdg-desktop-portal/tres-portals.conf`. The GTK portal backend
handles file selection and ordinary desktop requests; the wlroots backend
handles Screenshot and ScreenCast. Tres exports its Wayland socket and desktop
identity to D-Bus-activated services. User-created portal configurations are
**not overwritten**. Screen sharing also requires working PipeWire and
application compatibility; virtual-display tests cannot prove every browser
works on every GPU.

The right-square audio controls use `wpctl` if available, or `pactl`
otherwise. Unavailable controls are reported rather than silently ignored.
The package recommends the desktop portal backends; audio clients can be
installed independently if they are missing.

## Graphical administrator authentication

Tres starts the lightweight `lxpolkit` authentication agent in its own session,
so applications such as Synaptic can display a password prompt when requesting
administrator privileges. The source installer installs `lxpolkit` automatically.
For an existing manual installation, update with `bash scripts/update-panel.sh`;
if it reports a missing agent, run `sudo apt-get install lxpolkit` and log out
and back into Tres. The Debian package depends on `lxpolkit`.

The installer only adds a Tres-owned startup entry to existing configuration;
it does not change other desktop sessions. If the agent fails, inspect
`~/.cache/tres/polkit.log`. A successful authentication prompt does not guarantee
Synaptic itself can run as root under every Wayland configuration.

## Panel recovery

If the three squares disappear unexpectedly, the Tres panel supervisor
normally restarts them while the compositor is running. You can also
right-click an empty area of the desktop and select **Restart Tres Panel**.
Upgrading an existing manual Tres installation preserves a copy of any
recognized autostart file before updating its panel-launch line.
If you customized that line manually, inspect it before changing it.

## Why Labwc?

Labwc is a lightweight standalone **Wayland compositor**. Tres uses Labwc
as an independent session, selected separately at the login screen.
It doesn't rely on X11/Openbox, and its window selector uses wlroots's native
`wlr-foreign-toplevel-management` through `wlrctl`.

**Hybrid graphics caution:** a Wayland session does **not** guarantee a given
GPU/driver combination works with Labwc. Test the nested session first, then
try the dedicated login session. Keep your existing desktop as a fallback.

## Debian package (experimental)

An installable `.deb` and unsigned Debian source package are built by the
[Debian package workflow](.github/workflows/debian-package.yml).

See [the packaging guide](packaging/README.md) before installing. In
particular, **existing users of the GitHub shell installer need to migrate
their autostart file** so the login session runs the package-managed panel.
This is not yet a package in Ubuntu's official archive.

## Installation (apt-based Linux distributions)

Clone this repository and run the installer from inside it:

```bash
git clone https://github.com/Drmgiver/Tres.git
cd Tres
bash install.sh
```

The installer:
- Installs `labwc`, `python3-gi`, GTK3 bindings, `wlrctl`, `foot`,
  `swaybg`, `grim`, `slurp`, `wlr-randr`, and the Wayland portal
  backends through apt.
- Installs Tres files into `~/.local/share/tres/` and launcher
  `~/.local/bin/tres-panel`.
- Creates a **private** `~/.config/tres/labwc/` configuration (without
  editing `~/.config/labwc/` or other desktops' settings).
- Adds **Tres** to your login manager's session list with a small
  system-wide wrapper and `.desktop` file, requiring `sudo`.

**Test it nested** *inside another Wayland desktop* before logging into it:

```bash
bash scripts/test-nested.sh
```

A nested Wayland compositor should appear in its own window. It is *not* a
perfect test of native hybrid-GPU startup. Use Alt+F4 to close that window.

Then log out, choose **Tres** at your login screen, and sign in.
If no login session selector is visible, check your display manager's UI.
Your other installed desktop sessions remain available.

## Upgrading an existing Tres-Labwc installation

If you previously installed Tres from the old `tres-labwc` repository,
**keep your working desktop available** during the rename. Pull or clone
this repository, then **before** installing the renamed standalone session:

```bash
bash scripts/migrate-legacy.sh
bash install.sh
```

The migration script **copies** `~/.config/tres-labwc/` to
`~/.config/tres/` when the new destination is absent. It keeps your
HiDPI scaling and any GPU preference. It never deletes or overwrites the
original settings. The former login entry may remain available until you
explicitly clean up the old shell installation.

Users of the old experimental `tres-labwc` .deb should instead follow the
[package migration guide](packaging/README.md), which describes replacement
by the new `tres` package.

## Updating from GitHub

For routine code fixes after the initial installation, **no sudo or apt needed**:

```bash
git pull --ff-only
bash scripts/update-panel.sh
bash scripts/diagnose.sh
bash scripts/test-nested.sh
```

Close an earlier nested Labwc test window before restarting it. The new code
is loaded when Labwc starts the panel again. Run `bash install.sh` only for the
first setup or when dependencies/session installation change. The installer
preserves an existing Tres autostart file, so user customizations won't be
overwritten.

## Standalone black screen on AMD/NVIDIA hybrid laptops

The built-in screen can be attached to AMD even when an NVIDIA GPU is also
present. When the Labwc login is black but nested Labwc works, inspect the
compositor log and try selecting the AMD DRM card **for Tres only**.

From the existing repository checkout in a working desktop login:

```bash
git pull --ff-only
bash scripts/update-session.sh
bash scripts/try-amd-gpu.sh
```

The first command pulls the fix; the second updates only the Tres login
wrapper (one sudo file install, no apt), and the third verifies that the
known PCI device `0000:65:00.0` is using `amdgpu` before storing a
per-user preference. **This PCI address is specific to the original test
laptop; do not use the AMD helper blindly on other computers.**

Now save your work, log out and try **Tres** again. If the screen
goes black, return to another working desktop and collect:

```bash
bash scripts/diagnose-standalone.sh
```

The launcher keeps Labwc's `-d` debug output in
`~/.cache/tres/labwc-standalone.log`, including across a failed login.
The diagnostic prioritizes that log and connected DRM outputs instead of
filling the report with unrelated NVIDIA X11 mode lines. Review log
contents for private identifiers before sharing.

To **undo** the Tres-only GPU choice:

```bash
bash scripts/clear-gpu-override.sh
```

This does not modify GPU drivers, system-wide configurations, or other desktops.
The AMD selection is an investigation, not proof of the cause; a failed
attempt should be followed by review of the debug log.

## Display scaling (HiDPI laptops)

If all windows and the three squares appear too small in standalone Tres,
you need **Labwc output scaling**, not a different resolution. Run these
commands **inside Tres**, not another desktop session:

```bash
sudo apt install wlr-randr
wlr-randr
```

Find your built-in display's name (often `eDP-1`), then try 150%:

```bash
wlr-randr --output eDP-1 --scale 1.5
```

Replace `eDP-1` with the actual output name. Once you like the appearance,
**persist it only in the Tres session** with:

```bash
bash scripts/set-scale.sh eDP-1 1.5
```

The helper first applies the scale, then adds a clearly marked block to
`~/.config/tres/labwc/autostart`. It does not change another session's
scaling. To change it again, rerun with a different factor. Use `1.25`,
`1.5`, `1.75`, or `2` according to your display. If you have multiple
monitors, repeat the command for each output you want to configure. Tres
preserves each output's scale setting independently without erasing the others.

## Shortcuts & recovery

Labwc default keyboard shortcuts remain available (we don't override `rc.xml`):

| Key | Action |
| --- | --- |
| Super+Enter | Terminal (usually `foot`) |
| Alt+Tab | Switch windows |
| Alt+F4 | Close window |
| Right-click empty desktop | Labwc's basic root menu |

To diagnose missing menus or applets:

```bash
bash scripts/diagnose.sh
cat ~/.cache/tres/panel.log
```

If the panel log mentions `Gdk` version `4.0` already loaded, pull the latest
version and run `bash scripts/update-panel.sh` to install the corrected GTK3
bootstrap. The diagnostic now checks the exact same GDK 3/GTK 3 import path as
the panel itself.

If a graphical login is unusable, switch to a text TTY (often Ctrl+Alt+F3),
log in, and run `bash uninstall.sh` from your repository checkout, then reboot
or return to the login screen. **Keep another working desktop installed** for recovery.

## Uninstall

```bash
bash uninstall.sh
```

This removes the Tres login entry and installed panel. Your custom Tres
configuration and apt dependencies are left in place; **other desktops are unchanged**.

## Restart and shut down

Open the **rightmost white square** to find:

- **Exit Tres session…**: log out to the login screen, leaving the computer on.
- **Restart computer…**: request a normal system reboot.
- **Shut down computer…**: request a normal system poweroff.

Each action asks for confirmation. Restart and shutdown use
`systemctl reboot` / `systemctl poweroff` through the host's systemd/logind,
**without `sudo`, `--force`, or forcibly terminating applications**.
Save work before confirming. If the session's permissions or inhibitors block
a request, Tres displays the reported error instead of silently doing nothing.

The controls have not yet been hardware-tested across different login managers
or permission-agent configurations.

## Window stacking

Tres uses the Wayland **bottom** layer with no exclusive zone, above the
wallpaper but below ordinary windows. A maximized window therefore covers the
three squares, using all of the available screen. Normal windows can also cover
them. The squares reappear when the top-center desktop area is visible.

After pulling the update, run `bash scripts/update-panel.sh` and log out
and back into Tres to reload the panel.

## Known limitations

- Verified on a hybrid-graphics Linux laptop, but **not yet tested across
  a broad range of Linux distributions, display managers, and GPU models**.
- Applet menu is launchers and basic controls, not a full replacement for a
  desktop's network, Bluetooth, tray, notification, session/power, or battery
  management services. Some machines may still need a network applet, polkit
  agent, power service, or notification daemon.
- The running-window list uses `wlrctl`'s textual display, and identical
  app/title pairs cannot be uniquely distinguished. Unexpected formatting may
  require fixes after the first hardware test.
- Wayland portal preferences are configured for Tres, but real-world
  browser screen sharing and advanced GPU behavior still need broader testing.
- The application menu lists `.desktop` applications visible to Gio; hidden
  or command-line-only programs are omitted.

## Development

Run the GUI on a Wayland layer-shell-capable session:

```bash
/usr/bin/python3 src/tres_panel.py
```

Run non-GUI tests:

```bash
python3 -m unittest discover -s tests -v
```

Licensed under **GNU GPL v3** (matching this repository's existing LICENSE).
Independent project; not affiliated with original LiteStep or Tres creators.
