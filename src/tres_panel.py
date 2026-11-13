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
from tres_position import (read_position, save_position, coordinates, with_coordinates,
                           panel_size, reservation_depth)  # noqa: E402
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
        # Explicit top-left anchors avoid relying on compositor implicit centering.
        # Both axes use screen-relative margins, so any edge can be selected.
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)
        self._position = read_position()
        self._drag = None
        self._suppress_click = False
        self._layout_mode = None
        self._reservation_window = None
        self._reservation_config = None
        self._apply_mode(read_mode())
        box = Gtk.Box(
            orientation=(Gtk.Orientation.VERTICAL
                         if self._position["edge"] in ("left", "right")
                         else Gtk.Orientation.HORIZONTAL),
            spacing=5,
        )
        self._box = box
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
            btn.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                           Gdk.EventMask.BUTTON_RELEASE_MASK |
                           Gdk.EventMask.POINTER_MOTION_MASK)
            btn.connect("button-press-event", self._drag_press)
            btn.connect("motion-notify-event", self._drag_motion)
            btn.connect("button-release-event", self._drag_release)
            btn.connect("clicked", self.open_menu, builder)
            box.pack_start(btn, False, False, 0)
            self.square_buttons.append(btn)
        self.window.add(box)
        self.window.connect("size-allocate", self._on_size_allocate)
        self.window.show_all()
        self._apply_position(self._position)
        # A change made in the separate right-click configuration dialog
        # takes effect without restarting the desktop or the panel.
        GLib.timeout_add_seconds(1, self._check_settings)

    def _monitor_dimensions(self):
        monitor = GtkLayerShell.get_monitor(self.window)
        if monitor is None:
            display = Gdk.Display.get_default()
            monitor = display.get_primary_monitor() or display.get_monitor(0)
        if monitor is None:
            return None
        geometry = monitor.get_geometry()
        return geometry.width, geometry.height

    def _panel_dimensions(self):
        # Get the box's preferred size instead of an old window allocation:
        # after changing from horizontal to vertical, the old allocation
        # remains wide for a short time and would throw off all four edges.
        width, height = panel_size(self._appearance["square_size"],
                                   self._position["edge"])
        minimum, natural = self._box.get_preferred_size()
        return max(width, natural.width), max(height, natural.height)

    def _set_orientation(self, edge):
        orientation = (Gtk.Orientation.VERTICAL if edge in ("left", "right")
                       else Gtk.Orientation.HORIZONTAL)
        if self._box.get_orientation() != orientation:
            self._box.set_orientation(orientation)
            self._box.queue_resize()
            # Tell GTK/Wayland to recalculate the surface geometry instead of
            # retaining the wide allocation after switching to a side edge.
            self.window.resize(*panel_size(self._appearance["square_size"], edge))

    def _reserve_work_area(self, position, x, y, width, height, monitor):
        # The panel is a freely positioned TOP-layer window. Reserving space
        # from this same corner-anchored surface is invalid in layer-shell:
        # a positive exclusive zone requires a well-defined single edge.
        # Use an invisible dedicated edge-anchored surface for work-area
        # reservation, while keeping the actual three squares movable.
        if self._layout_mode != "reserved":
            if self._reservation_window is not None:
                self._reservation_window.destroy()
                self._reservation_window = None
                self._reservation_config = None
            return

        edge = position["edge"]
        depth = reservation_depth(edge, x, y, width, height, *monitor)
        config = (edge, depth)
        if config == self._reservation_config:
            return
        if self._reservation_window is None:
            reserver = Gtk.Window()
            reserver.set_decorated(False)
            reserver.set_resizable(False)
            reserver.set_app_paintable(True)
            reserver.set_opacity(0)
            reserver.set_size_request(1, 1)
            GtkLayerShell.init_for_window(reserver)
            GtkLayerShell.set_layer(reserver, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_keyboard_mode(
                reserver, GtkLayerShell.KeyboardMode.NONE)
            self._reservation_window = reserver
        reserver = self._reservation_window
        anchors = {
            "top": (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.LEFT,
                    GtkLayerShell.Edge.RIGHT),
            "bottom": (GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT,
                       GtkLayerShell.Edge.RIGHT),
            "left": (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.TOP,
                     GtkLayerShell.Edge.BOTTOM),
            "right": (GtkLayerShell.Edge.RIGHT, GtkLayerShell.Edge.TOP,
                      GtkLayerShell.Edge.BOTTOM),
        }
        for anchor in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                       GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(reserver, anchor, anchor in anchors[edge])
            GtkLayerShell.set_margin(reserver, anchor, 0)
        GtkLayerShell.set_exclusive_zone(reserver, depth)
        reserver.show_all()
        self._reservation_config = config

    def _apply_position(self, position):
        monitor = self._monitor_dimensions()
        if monitor is None:
            return
        self._set_orientation(position["edge"])
        width, height = self._panel_dimensions()
        x, y = coordinates(position, width, height, *monitor)

        # Match the physical edge. Bottom is anchored to BOTTOM, right to
        # RIGHT: neither relies on a top-left margin spanning the monitor.
        edge = position["edge"]
        anchors = {
            "top": (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.LEFT),
            "bottom": (GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT),
            "left": (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.TOP),
            "right": (GtkLayerShell.Edge.RIGHT, GtkLayerShell.Edge.TOP),
        }
        margins = {
            GtkLayerShell.Edge.LEFT: x,
            GtkLayerShell.Edge.RIGHT: monitor[0] - x - width,
            GtkLayerShell.Edge.TOP: y,
            GtkLayerShell.Edge.BOTTOM: monitor[1] - y - height,
        }
        for anchor in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                       GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            enabled = anchor in anchors[edge]
            if GtkLayerShell.get_anchor(self.window, anchor) != enabled:
                GtkLayerShell.set_anchor(self.window, anchor, enabled)
            desired = margins[anchor] if enabled else 0
            if GtkLayerShell.get_margin(self.window, anchor) != desired:
                GtkLayerShell.set_margin(self.window, anchor, desired)
        self._reserve_work_area(position, x, y, width, height, monitor)

    def _on_size_allocate(self, _window, _allocation):
        if self._drag is None:
            self._apply_position(self._position)

    def _drag_press(self, _button, event):
        if event.button != 1 or not (event.state & Gdk.ModifierType.SUPER_MASK):
            return False
        monitor = self._monitor_dimensions()
        if monitor is None:
            return False
        width, height = self._panel_dimensions()
        x, y = coordinates(self._position, width, height, *monitor)
        self._drag = (float(event.x_root), float(event.y_root), x, y, False)
        self._suppress_click = False
        return True

    def _drag_motion(self, _button, event):
        if self._drag is None:
            return False
        start_x, start_y, initial_x, initial_y, moved = self._drag
        dx, dy = float(event.x_root) - start_x, float(event.y_root) - start_y
        if not moved and abs(dx) + abs(dy) < 3:
            return True
        monitor = self._monitor_dimensions()
        if monitor is None:
            return True
        width, height = self._panel_dimensions()
        new_x = max(0, min(monitor[0] - width, round(initial_x + dx)))
        new_y = max(0, min(monitor[1] - height, round(initial_y + dy)))
        # Keep the selected edge, but move freely using offsets on both axes.
        self._position = with_coordinates(self._position["edge"], new_x, new_y,
                                          width, height, *monitor)
        self._drag = (start_x, start_y, initial_x, initial_y, True)
        self._apply_position(self._position)
        return True

    def _drag_release(self, _button, event):
        if self._drag is None or event.button != 1:
            return False
        moved = self._drag[4]
        self._drag = None
        if moved:
            self._suppress_click = True
            try:
                save_position(self._position)
            except OSError as error:
                print(f"Could not save Tres panel position: {error}", file=sys.stderr)
        return True

    def _apply_mode(self, mode: str) -> None:
        if mode not in ("under", "over", "reserved"):
            raise ValueError(f"Unknown Tres stacking mode: {mode}")
        # Keep the visible squares pinned to their physical screen position.
        # An exclusive zone of 0 makes layer-shell move the panel OUT of a
        # reserved region, producing the user-visible downward jump. -1 means
        # ignore reservations from other surfaces; our separate edge-anchored
        # surface still reserves the work area for normal windows.
        GtkLayerShell.set_exclusive_zone(self.window, -1)
        GtkLayerShell.set_layer(
            self.window,
            GtkLayerShell.Layer.BOTTOM if mode == "under"
            else GtkLayerShell.Layer.TOP,
        )
        self._layout_mode = mode
        if hasattr(self, "_box"):
            self._apply_position(self._position)

    def _check_settings(self) -> bool:
        mode = read_mode()
        if mode != self._layout_mode:
            self._apply_mode(mode)
        latest_position = read_position()
        if self._drag is None and latest_position != self._position:
            self._position = latest_position
            self._apply_position(self._position)
        current = read_appearance()
        if current != self._appearance:
            self._css.load_from_data(panel_style(current))
            if current["square_size"] != self._appearance["square_size"]:
                for button in self.square_buttons:
                    button.set_size_request(current["square_size"],
                                            current["square_size"])
                self.window.queue_resize()
            self._appearance = current
            self._apply_position(self._position)
        return True

    def open_menu(self, button, builder) -> None:
        if self._suppress_click:
            self._suppress_click = False
            return
        menu = builder()
        menu.show_all()
        if self._position["edge"] == "left":
            from_gravity, to_gravity = Gdk.Gravity.EAST, Gdk.Gravity.WEST
        elif self._position["edge"] == "right":
            from_gravity, to_gravity = Gdk.Gravity.WEST, Gdk.Gravity.EAST
        elif self._position["edge"] == "bottom":
            from_gravity, to_gravity = Gdk.Gravity.NORTH, Gdk.Gravity.SOUTH
        else:
            from_gravity, to_gravity = Gdk.Gravity.SOUTH, Gdk.Gravity.NORTH
        menu.popup_at_widget(button, from_gravity, to_gravity, None)

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
