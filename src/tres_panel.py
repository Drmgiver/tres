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
except (ImportError, ValueError) as error:
    sys.exit(f"GTK3 layer-shell not installed: {error}\nRun bash install.sh")

from tres_core import activate, windows  # noqa: E402

STYLE = b"""
window#tres-root { background-color: transparent; }
button.tres-square {
    min-width: 19px; min-height: 19px;
    padding: 0; margin: 0;
    border: 0; border-radius: 0;
    background-image: none; background-color: #ffffff;
    box-shadow: none;
}
button.tres-square:hover { background-color: #d8d8d8; }
button.tres-square:active { background-color: #aaaaaa; }
"""

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

        css = Gtk.CssProvider()
        css.load_from_data(STYLE)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        GtkLayerShell.init_for_window(self.window)
        # Bottom layer is above wallpaper, but below normal windows.
        # A maximized window should cover all three squares naturally.
        GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.BOTTOM)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.TOP, 3)
        GtkLayerShell.set_exclusive_zone(self.window, 0)
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        for tooltip, builder in (("Applications", self.applications_menu),
                                 ("Running windows", self.windows_menu),
                                 ("Applets", self.applets_menu)):
            btn = Gtk.Button()
            btn.set_size_request(19, 19)
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.get_style_context().add_class("tres-square")
            btn.set_tooltip_text(tooltip)
            btn.connect("clicked", self.open_menu, builder)
            box.pack_start(btn, False, False, 0)
        self.window.add(box)
        self.window.show_all()

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
        found = {}
        for app in Gio.AppInfo.get_all():
            try:
                if not app.should_show() or not app.get_name():
                    continue
                found.setdefault(category(app), []).append(app)
            except Exception:
                continue
        for group in sorted(found):
            rows = []
            for app in sorted(found[group], key=lambda x: x.get_name().casefold()):
                rows.append(self.item(app.get_name(), lambda app=app: self.launch_app(app)))
            menu.append(self.submenu(group, rows))
        if not found:
            menu.append(self.item("No desktop applications found"))
        return menu

    @staticmethod
    def launch_app(app):
        try:
            app.launch([], None)
        except Exception as error:
            print(f"Tres: could not launch {app.get_name()}: {error}", file=sys.stderr)

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
        menu.append(self.item(datetime.now().strftime("%a %b %d, %Y  %H:%M")))
        menu.append(self.item(battery_label()))
        menu.append(self.separator())

        audio = [self.item("Volume +5%", lambda: self.audio("+5%")),
                 self.item("Volume -5%", lambda: self.audio("-5%")),
                 self.item("Mute/unmute", lambda: self.audio("toggle", mute=True))]
        if shutil.which("pavucontrol"):
            audio.append(self.item("Sound settings", lambda: spawn_first(("pavucontrol",))))
        menu.append(self.submenu("Audio", audio))

        utilities = [
            ("Network connections", ("nm-connection-editor",)),
            ("Bluetooth", ("blueman-manager",)),
            ("System settings", ("cosmic-settings",)),
            ("Power settings", ("xfce4-power-manager-settings",)),
            ("Files", ("cosmic-files", "--new-window")),
        ]
        for name, argv in utilities:
            if shutil.which(argv[0]):
                menu.append(self.item(name, lambda argv=argv: spawn_first(argv)))
        menu.append(self.item("Terminal", lambda: spawn_first(
            ("foot",), ("alacritty",), ("kitty",), ("cosmic-term",),
            ("gnome-terminal",), ("xterm",))))
        menu.append(self.separator())
        menu.append(self.item("Exit Tres session…", self.ask_exit))
        return menu

    @staticmethod
    def audio(level: str, mute: bool = False) -> None:
        if not shutil.which("pactl"):
            print("Tres: pactl not installed", file=sys.stderr)
            return
        args = ["pactl", "set-sink-mute" if mute else "set-sink-volume",
                "@DEFAULT_SINK@", level]
        subprocess.Popen(args, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
