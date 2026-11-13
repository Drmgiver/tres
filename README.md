# Tres for Linux (Labwc)

A **three-square, ultra-minimal Wayland desktop**, inspired by the old LiteStep
**Tres** theme. This is an original recreation, not original LiteStep theme code.

```
                  [■] [■] [■]
```

Three **blank, 19×19 white squares** centered 3px below the top of the display:

1. **Left:** installed applications, grouped in menus.
2. **Middle:** running windows; select one to activate it.
3. **Right:** clock, battery, audio, network/settings launchers and log out.

No permanent taskbar, dock, full-width panel, or reserved screen space.

## Why Labwc?

Labwc is a lightweight standalone **Wayland compositor**. Unlike the earlier
COSMIC-overlay prototype, Tres with Labwc runs **instead of** COSMIC at login.
It doesn't rely on X11/Openbox, and its window selector uses wlroots's native
`wlr-foreign-toplevel-management` through `wlrctl`.

**Hybrid graphics caution:** a Wayland session does **not** guarantee a given
GPU/driver combination works with Labwc. Test the nested session first, then
try the dedicated login session. Keep COSMIC installed as your fallback.

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
