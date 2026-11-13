# Tres for Linux (Labwc)

A **three-square, ultra-minimal Wayland desktop**, inspired by the old LiteStep
**Tres** theme. This is an original recreation, not original LiteStep theme code.

```
                  [■] [■] [■]
```

Three **blank, 19×19 white squares** centered 3px below the top of the display:

1. **Left:** installed applications, grouped in menus.
2. **Middle:** running windows; select one to activate it.
3. **Right:** clock, battery, audio, network/settings launchers, log out,
   restart, and shut down.

No permanent taskbar, dock, full-width panel, or reserved space.
The three squares sit above the wallpaper but **below normal windows**.
Maximized windows cover them completely.

## Why Labwc?

Labwc is a lightweight standalone **Wayland compositor**. Unlike the earlier
COSMIC-overlay prototype, Tres with Labwc runs **instead of** COSMIC at login.
It doesn't rely on X11/Openbox, and its window selector uses wlroots's native
`wlr-foreign-toplevel-management` through `wlrctl`.

**Hybrid graphics caution:** a Wayland session does **not** guarantee a given
GPU/driver combination works with Labwc. Test the nested session first, then
try the dedicated login session. Keep COSMIC installed as your fallback.

## Debian package (experimental)

An installable `.deb` and an unsigned Debian source package are built by the
[Debian package workflow](https://github.com/Drmgiver/tres-labwc/actions/workflows/debian-package.yml).

See [the packaging guide](packaging/README.md) before installing. In
particular, **existing users of the GitHub shell installer need to migrate
their autostart file** so the login session runs the package-managed panel.
This is not yet a package in Ubuntu's official archive.

## Installation (Pop!_OS / Ubuntu, apt)

Clone this repository and run the installer from inside it:

```bash
git clone https://github.com/Drmgiver/tres-labwc.git
cd tres-labwc
bash install.sh
```

The installer:
- Installs `labwc`, `python3-gi`, GTK3's introspection bindings,
  `gir1.2-gtklayershell-0.1`, `wlrctl`, `foot`, and `swaybg` through apt.
- Installs Tres files into `~/.local/share/tres-labwc/` and launcher
  `~/.local/bin/tres-panel`.
- Creates a **private** `~/.config/tres-labwc/labwc/` configuration (without
  editing `~/.config/labwc/` or COSMIC settings).
- Adds **Tres (Labwc)** to your login manager's session list with a small
  system-wide wrapper and `.desktop` file, requiring `sudo`.

**Test it nested** *inside COSMIC* before logging into it:

```bash
bash scripts/test-nested.sh
```

A nested Wayland compositor should appear in its own window. It is *not* a
perfect test of native hybrid-GPU startup. Use Alt+F4 to close that window.

Then log out, choose **Tres (Labwc)** at your login screen, and sign in.
If no login session selector is visible, check your display manager's UI.
The default COSMIC option remains available.

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

From the existing repository checkout in a working COSMIC login:

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

Now save your work, log out and try **Tres (Labwc)** again. If the screen
goes black, reboot into COSMIC and collect:

```bash
bash scripts/diagnose-standalone.sh
```

The launcher keeps Labwc's `-d` debug output in
`~/.cache/tres-labwc/labwc-standalone.log`, including across a failed login.
The diagnostic prioritizes that log and connected DRM outputs instead of
filling the report with unrelated NVIDIA X11 mode lines. Review log
contents for private identifiers before sharing.

To **undo** the Tres-only GPU choice:

```bash
bash scripts/clear-gpu-override.sh
```

This does not modify GPU drivers, system-wide configurations, or COSMIC.
The AMD selection is an investigation, not proof of the cause; a failed
attempt should be followed by review of the debug log.

## Display scaling (HiDPI laptops)

If all windows and the three squares appear too small in standalone Tres,
you need **Labwc output scaling**, not a different resolution. Run these
commands **inside Tres**, not inside COSMIC:

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
`~/.config/tres-labwc/labwc/autostart`. It does not change COSMIC's
scaling. To change it again, rerun with a different factor. Use `1.25`,
`1.5`, `1.75`, or `2` according to your display. If you have multiple
monitors, this simple helper currently remembers only one chosen output.

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
cat ~/.cache/tres-labwc/panel.log
```

If the panel log mentions `Gdk` version `4.0` already loaded, pull the latest
version and run `bash scripts/update-panel.sh` to install the corrected GTK3
bootstrap. The diagnostic now checks the exact same GDK 3/GTK 3 import path as
the panel itself.

If a graphical login is unusable, switch to a text TTY (often Ctrl+Alt+F3),
log in, and run `bash uninstall.sh` from your repository checkout, then reboot
or return to the login screen. **Do not uninstall COSMIC** for this experiment.

## Uninstall

```bash
bash uninstall.sh
```

This removes the Tres login entry and installed panel. Your custom Tres
configuration and apt dependencies are left in place; **COSMIC is unchanged**.

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

- Prototype, **not verified yet on the target laptop**. Shell/Python tests are
  included, but a real graphical/hybrid GPU test is necessary.
- Applet menu is launchers and basic controls, not a full replacement for a
  desktop's network, Bluetooth, tray, notification, session/power, or battery
  management services. Depending on the machine you may need to add a
  network applet, polkit agent, portal, power service, and notification daemon.
- The running-window list uses `wlrctl`'s textual display, and identical
  app/title pairs cannot be uniquely distinguished. Unexpected formatting may
  require fixes after the first hardware test.
- Wayland screen sharing / portals and some advanced GPU behaviors have not
  been configured in this minimal prototype.
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
