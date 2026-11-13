#!/usr/bin/python3
"""Tres: a three-square GTK3 layer-shell panel for the Labwc Wayland session."""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def setup_gi():
    import gi
    # Explicitly pin GDK before importing any gi.repository symbols. On
    # installations with GTK 4, the implicit default otherwise loads GDK 4.
    gi.require_version("Gdk", "3.0")
    gi.require_version("Gtk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import Gdk, Gio, Gtk, GtkLayerShell
    return Gdk, Gio, Gtk, GtkLayerShell

try:
    Gdk, Gio, Gtk, GtkLayerShell = setup_gi()
    from gi.repository import GLib
except (ImportError, ValueError) as error:
    sys.exit(f"GTK3 layer-shell not installed: {error}\nRun bash install.sh")

from tres_core import activate, request_power_action, submenu_pages, windows  # noqa: E402
from tres_layout import read_mode  # noqa: E402
from tres_preferences import read_appearance  # noqa: E402
from tres_terminal import open_terminal as open_selected_terminal  # noqa: E402
from tres_audio import audio_backend, change_volume, volume_label, AudioError  # noqa: E402
from tres_applications import visible_applications, launch_application  # noqa: E402

def panel_style(appearance: dict) -> bytes:
    """Safe CSS: colors and size are strictly validated by tres_preferences."""
    size = appearance["square_size"]
    return f"""
window#tres-root {{ background-color: transparent; }}
button.tres-square {{
    min-width: {size}px; min-height: {size}px;
    padding: 0; margin: 0;
    border: 0; border-radius: 0;
    background-image: none; background-color: {appearance["square_color"]};
    box-shadow: none;
}}
button.tres-square:hover {{ background-color: {appearance["hover_color"]}; }}
button.tres-square:active {{ background-color: #aaaaaa; }}
""".encode("ascii")

CATEGORY_PRIORITY = (
    ("Accessories", ("Utility", "Accessories")),
    ("Development", ("Development",)),
    ("Games", ("Game",)),
    ("Graphics", ("Graphics",)),
    ("Internet", ("Network", "WebBrowser", "Email")),
    ("Multimedia", ("Audio", "Video", "AudioVideo")),
    ("Office", ("Office",)),
    ("Settings", ("Settings",)),
    ("System", ("System",)),
)


def spawn_first(*candidates: tuple[str, ...]) -> bool:
    for argv in candidates:
        if argv and shutil.which(argv[0]):
            subprocess.Popen(list(argv), start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    return False


def category(app) -> str:
    try:
        cats = set(filter(None, (app.get_categories() or "").split(";")))
    except (AttributeError, TypeError):
        cats = set()
    for label, values in CATEGORY_PRIORITY:
        if cats.intersection(values):
            return label
    return "Other"


def battery_label() -> str:
    battery_paths = sorted(glob.glob("/sys/class/power_supply/BAT*/capacity"))
    for path in battery_paths:
        try:
            return f"Battery: {Path(path).read_text().strip()}%"
        except (OSError, ValueError):
            continue
    return "Battery: not reported"


class Tres:
    def __init__(self) -> None:
        self.window = Gtk.Window()
        self.window.set_name("tres-root")
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.set_app_paintable(True)
        self.window.connect("destroy", Gtk.main_quit)
        screen = self.window.get_screen()
        if screen and screen.get_rgba_visual():
            self.window.set_visual(screen.get_rgba_visual())

        self._appearance = read_appearance()
        self._css = Gtk.CssProvider()
        self._css.load_from_data(panel_style(self._appearance))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self._css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.TOP, 3)
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)
        self._layout_mode = None
        self._apply_mode(read_mode())
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.square_buttons = []
        for tooltip, builder in (("Applications", self.applications_menu),
                                 ("Running windows", self.windows_menu),
                                 ("Applets", self.applets_menu)):
            btn = Gtk.Button()
            btn.set_size_request(self._appearance["square_size"],
                                 self._appearance["square_size"])
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.get_style_context().add_class("tres-square")
            btn.set_tooltip_text(tooltip)
            btn.connect("clicked", self.open_menu, builder)
            box.pack_start(btn, False, False, 0)
            self.square_buttons.append(btn)
        self.window.add(box)
        self.window.show_all()
        # A change made in the separate right-click configuration dialog
        # takes effect without restarting the desktop or the panel.
        GLib.timeout_add_seconds(1, self._check_settings)

    def _apply_mode(self, mode: str) -> None:
        if mode == "under":
            # Above the wallpaper but beneath normal and maximized windows.
            GtkLayerShell.set_exclusive_zone(self.window, 0)
            GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.BOTTOM)
        elif mode == "over":
            # Always visible over normal/maximized windows, no lost screen space.
            GtkLayerShell.set_exclusive_zone(self.window, 0)
            GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.TOP)
        elif mode == "reserved":
            # The compositor allocates a strip equal to the squares plus margin.
            GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.TOP)
            GtkLayerShell.auto_exclusive_zone_enable(self.window)
        else:
            raise ValueError(f"Unknown Tres stacking mode: {mode}")
        self._layout_mode = mode

    def _check_settings(self) -> bool:
        mode = read_mode()
        if mode != self._layout_mode:
            self._apply_mode(mode)
        current = read_appearance()
        if current != self._appearance:
            self._css.load_from_data(panel_style(current))
            if current["square_size"] != self._appearance["square_size"]:
                for button in self.square_buttons:
                    button.set_size_request(current["square_size"],
                                            current["square_size"])
                self.window.queue_resize()
            self._appearance = current
        return True

    def open_menu(self, button, builder) -> None:
        menu = builder()
        menu.show_all()
        menu.popup_at_widget(button, Gdk.Gravity.SOUTH, Gdk.Gravity.NORTH, None)

    @staticmethod
    def item(label: str, callback=None) -> object:
        entry = Gtk.MenuItem.new_with_label(label)
        if callback is not None:
            entry.connect("activate", lambda _entry: callback())
        else:
            entry.set_sensitive(False)
        return entry

    @staticmethod
    def separator():
        return Gtk.SeparatorMenuItem()

    @staticmethod
    def submenu(label: str, rows):
        parent = Gtk.MenuItem.new_with_label(label)
        nested = Gtk.Menu()
        for row in rows:
            nested.append(row)
        parent.set_submenu(nested)
        return parent

    def applications_menu(self):
        menu = Gtk.Menu()
        menu.append(self.item("Search Applications…", lambda: spawn_first(
            (str(Path.home() / ".local/bin/tres-search"),),
            ("/usr/bin/tres-search",))))
        menu.append(self.separator())
        found = {}
        for app in visible_applications(Gio):
            found.setdefault(category(app), []).append(app)
        for group in sorted(found):
            apps = sorted(found[group], key=lambda x: x.get_name().casefold())
            menu.append(self.submenu(group, self._application_rows(apps)))
        if not found:
            menu.append(self.item("No desktop applications found"))
        return menu

    def _application_rows(self, apps, offset=0):
        """Keep GTK3 menus short so Wayland never hides the final apps.

        GTK3's tall-menu scrolling is unreliable under Wayland. Instead of
        depending on scroll arrows, large categories have numbered submenus.
        A single menu never contains more than 12 app/page entries.
        """
        sections = submenu_pages(len(apps))
        if len(sections) <= 1:
            return [
                self.item(app.get_name(), lambda app=app: self.launch_app(app))
                for app in apps
            ]
        return [
            self.submenu(
                f"Apps {offset + start + 1}–{offset + end}",
                self._application_rows(apps[start:end], offset + start),
            )
            for start, end in sections
        ]

    @staticmethod
    def launch_app(app):
        return launch_application(app)

    def windows_menu(self):
        menu = Gtk.Menu()
        try:
            running = windows()
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            menu.append(self.item("Window list unavailable"))
            print(f"Tres window list: {error}", file=sys.stderr)
            return menu
        if not running:
            menu.append(self.item("No open windows"))
        for top in running:
            label = top.title if len(top.title) <= 75 else top.title[:72] + "..."
            menu.append(self.item(label, lambda top=top: self.focus(top)))
        return menu

    @staticmethod
    def focus(top):
        try:
            activate(top)
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            print(f"Tres: focus failed: {error}", file=sys.stderr)

    def applets_menu(self):
        menu = Gtk.Menu()
        menu.append(self.item(datetime.now().strftime("%a %b %d, %Y  %-I:%M %p")))
        menu.append(self.item(battery_label()))
        menu.append(self.item(volume_label()))
        menu.append(self.separator())

        if audio_backend() is not None:
            audio = [self.item("Volume +5%", lambda: self.audio("up")),
                     self.item("Volume -5%", lambda: self.audio("down")),
                     self.item("Mute/unmute", lambda: self.audio("mute"))]
        else:
            audio = [self.item("Audio controls unavailable")]
        if shutil.which("pavucontrol"):
            audio.append(self.item("Sound settings", lambda: spawn_first(("pavucontrol",))))
        menu.append(self.submenu("Audio", audio))

        # Tres runs as its own Labwc session. Do not launch settings panels
        # requiring services provided by a different desktop environment.
        # Use the same Tres dialog as the desktop right-click menu instead.
        menu.append(self.item("Reconfigure Tres…", lambda: spawn_first(
            (str(Path.home() / ".local/bin/tres-config"),),
            ("/usr/bin/tres-config",))))

        utilities = [
            ("Network connections", ("nm-connection-editor",)),
            ("Bluetooth", ("blueman-manager",)),
            ("Power settings", ("xfce4-power-manager-settings",)),
        ]
        for name, argv in utilities:
            if shutil.which(argv[0]):
                menu.append(self.item(name, lambda argv=argv: spawn_first(argv)))
        menu.append(self.item("Files", lambda: spawn_first(
            (str(Path.home() / ".local/bin/tres-open-files"),),
            ("/usr/bin/tres-open-files",))))
        menu.append(self.item("Terminal", self.open_terminal))
        menu.append(self.separator())
        menu.append(self.item("Exit Tres session…", self.ask_exit))
        menu.append(self.item("Restart computer…", lambda: self.confirm_power("restart")))
        menu.append(self.item("Shut down computer…", lambda: self.confirm_power("shutdown")))
        return menu

    @staticmethod
    def open_terminal() -> None:
        try:
            open_selected_terminal()
        except RuntimeError as error:
            print(f"Tres: terminal could not launch: {error}", file=sys.stderr)

    def audio(self, direction: str) -> None:
        try:
            change_volume(direction)
        except (AudioError, OSError) as error:
            problem = Gtk.MessageDialog(
                transient_for=self.window, flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE,
                text="Tres could not change the volume",
            )
            problem.format_secondary_text(str(error)[:500])
            problem.run()
            problem.destroy()

    def confirm_power(self, action: str) -> None:
        # Confirmation is deliberately separate for restart and poweroff.
        messages = {
            "restart": "Restart this computer?",
            "shutdown": "Shut down this computer?",
        }
        if action not in messages:
            return
        dialog = Gtk.MessageDialog(
            transient_for=self.window, flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO, text=messages[action],
        )
        dialog.format_secondary_text("Save your work first. Unsaved changes may be lost.")
        choice = dialog.run()
        dialog.destroy()
        if choice != Gtk.ResponseType.YES:
            return
        try:
            request_power_action(action)
        except RuntimeError as error:
            problem = Gtk.MessageDialog(
                transient_for=self.window, flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE,
                text="Unable to " + ("restart" if action == "restart" else "shut down"),
            )
            problem.format_secondary_text(str(error)[:400])
            problem.run()
            problem.destroy()

    def ask_exit(self):
        dialog = Gtk.MessageDialog(transient_for=self.window, flags=Gtk.DialogFlags.MODAL,
                                   message_type=Gtk.MessageType.QUESTION,
                                   buttons=Gtk.ButtonsType.YES_NO,
                                   text="Log out of Tres?")
        dialog.format_secondary_text("Your running applications will be closed.")
        answer = dialog.run()
        dialog.destroy()
        if answer == Gtk.ResponseType.YES:
            spawn_first(("labwc", "--exit"))


def main():
    if not os.environ.get("WAYLAND_DISPLAY"):
        sys.exit("Tres requires a Wayland session (WAYLAND_DISPLAY is missing).")
    Tres()
    Gtk.main()


if __name__ == "__main__":
    main()
