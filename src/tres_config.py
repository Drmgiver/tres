#!/usr/bin/python3
"""Reconfigure Tres: self-contained GTK3 settings for the Labwc desktop."""
from __future__ import annotations

import os
import shutil
import sys

from tres_display import DisplayError, apply_scale, output_info
from tres_open import _is_cosmic
from tres_layout import MODES, read_mode, save_mode
from tres_preferences import (DEFAULT_APPEARANCE, TERMINALS, read_appearance,
                              read_terminal, save_appearance, save_terminal)
from tres_shortcuts import DEFAULT_KEYS, read_shortcuts, reload_labwc, save_shortcuts

POSITIONS = (
    ("under", "Under", "Normal and maximized windows can cover the squares."),
    ("over", "Over", "The squares stay above windows without reserving space."),
    ("reserved", "Space reserved", "Maximized windows leave room for the squares."),
)
MIME_CHOICES = (
    ("File manager", "inode/directory"),
    ("Web browser", "x-scheme-handler/https"),
    ("Email", "x-scheme-handler/mailto"),
    ("Text editor", "text/plain"),
    ("PDF viewer", "application/pdf"),
)


def main() -> None:
    import gi
    gi.require_version("Gdk", "3.0")
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gdk, Gio, Gtk

    def label(text: str, wrap: bool = False):
        widget = Gtk.Label(label=text)
        widget.set_xalign(0)
        if wrap:
            widget.set_line_wrap(True)
        return widget

    def title(text):
        widget = label(text)
        widget.set_markup("<b>" + text + "</b>")
        return widget

    def row(*widgets):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        for widget in widgets:
            box.pack_start(widget, False, False, 0)
        return box

    def page(notebook, name):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(14)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(box)
        notebook.append_page(scroll, label(name))
        return box

    def color_picker(value):
        rgba = Gdk.RGBA()
        rgba.parse(value)
        return Gtk.ColorButton.new_with_rgba(rgba)

    def rgb_hex(widget):
        rgba = widget.get_rgba()
        return "#{:02x}{:02x}{:02x}".format(
            round(rgba.red * 255), round(rgba.green * 255),
            round(rgba.blue * 255),
        )

    window = Gtk.Window(title="Reconfigure Tres")
    window.set_default_size(580, 470)
    window.set_border_width(6)
    window.connect("destroy", Gtk.main_quit)
    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    window.add(outer)
    notebook = Gtk.Notebook()
    outer.pack_start(notebook, True, True, 0)
    close = Gtk.Button(label="Close")
    close.connect("clicked", lambda _button: window.destroy())
    footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    footer.set_margin_end(8)
    footer.set_margin_bottom(8)
    footer.pack_end(close, False, False, 0)
    outer.pack_start(footer, False, False, 0)

    def message(text, error=False):
        dialog = Gtk.MessageDialog(
            transient_for=window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR if error else Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.CLOSE,
            text="Tres settings" if not error else "Unable to apply setting",
        )
        dialog.format_secondary_text(str(text)[:700])
        dialog.run()
        dialog.destroy()

    def attempt(callback):
        try:
            result = callback()
        except (ValueError, OSError, RuntimeError, GLibError) as error:
            message(error, error=True)
            return
        if result:
            message(result)

    # GLib errors are exposed through gi.repository.GLib when saving defaults.
    from gi.repository import GLib
    GLibError = GLib.Error

    # Appearance: preserve the current three-square positioning UI.
    appearance = page(notebook, "Appearance")
    appearance.pack_start(title("Three-square position"), False, False, 0)
    mode_buttons = {}
    group = None
    for key, name, detail in POSITIONS:
        button = (Gtk.RadioButton.new_with_label_from_widget(group, name)
                  if group else Gtk.RadioButton.new_with_label(None, name))
        if group is None:
            group = button
        appearance.pack_start(button, False, False, 0)
        description = label(detail, True)
        description.set_margin_start(23)
        appearance.pack_start(description, False, False, 0)
        mode_buttons[key] = button
    mode_buttons[read_mode()].set_active(True)

    original = read_appearance()
    appearance.pack_start(title("Square appearance"), False, False, 0)
    square = color_picker(original["square_color"])
    hover = color_picker(original["hover_color"])
    background = color_picker(original["wallpaper_color"])
    size = Gtk.SpinButton.new_with_range(15, 40, 1)
    size.set_value(original["square_size"])
    appearance.pack_start(row(label("Square color:"), square,
                              label("Hover color:"), hover), False, False, 0)
    appearance.pack_start(row(label("Square size (pixels):"), size), False, False, 0)
    appearance.pack_start(row(label("Wallpaper color:"), background), False, False, 0)
    appearance.pack_start(label(
        "The squares update immediately. Wallpaper color applies on the next "
        "Tres login when using the supplied wallpaper autostart.", True
    ), False, False, 0)

    def apply_appearance(_button):
        def action():
            choice = next(key for key in MODES if mode_buttons[key].get_active())
            new_values = {
                "square_color": rgb_hex(square),
                "hover_color": rgb_hex(hover),
                "square_size": size.get_value_as_int(),
                "wallpaper_color": rgb_hex(background),
            }
            save_appearance(new_values)
            save_mode(choice)
            return "Appearance saved. Wallpaper changes take effect at next login."
        attempt(action)

    apply_button = Gtk.Button(label="Apply appearance")
    apply_button.connect("clicked", apply_appearance)
    appearance.pack_start(apply_button, False, False, 0)

    # Display scaling: read actual Wayland outputs, not COSMIC display settings.
    display = page(notebook, "Display")
    display.pack_start(title("Display scale"), False, False, 0)
    display.pack_start(label(
        "This affects only the active Tres/Labwc session, not COSMIC. "
        "Your saved scale will be restored at the next Tres login.", True
    ), False, False, 0)
    output = Gtk.ComboBoxText()
    scale = Gtk.SpinButton.new_with_range(0.75, 3.0, 0.25)
    scale.set_digits(2)
    scale.set_value(1.0)
    try:
        connected = output_info()
        for name, factor in connected:
            output.append(name, name)
        if connected:
            output.set_active(0)
            scale.set_value(connected[0][1])
            output.connect("changed",
                           lambda widget: scale.set_value(next(
                               (factor for name, factor in connected
                                if name == widget.get_active_id()), 1.0)))
        else:
            display.pack_start(label("No active Wayland outputs were found."),
                               False, False, 0)
    except DisplayError as error:
        connected = []
        display.pack_start(label(str(error), True), False, False, 0)
    display.pack_start(row(label("Output:"), output), False, False, 0)
    display.pack_start(row(label("Scaling:"), scale), False, False, 0)
    set_scale = Gtk.Button(label="Apply display scale")
    set_scale.set_sensitive(bool(connected))
    set_scale.connect("clicked", lambda _button: attempt(
        lambda: (apply_scale(output.get_active_id(), scale.get_value()),
                 "Scale applied and saved.")[1]))
    display.pack_start(set_scale, False, False, 0)

    # Keyboard: own only a marked region of the user's private Labwc rc.xml.
    keyboard = page(notebook, "Keyboard")
    keyboard.pack_start(title("Keyboard shortcuts"), False, False, 0)
    keyboard.pack_start(label(
        "Labwc notation: W=Super, A=Alt, C=Ctrl, S=Shift. "
        "Examples: Print, W-e, W-Return. Clear a field to disable its "
        "Tres shortcut. Existing non-Tres keybindings are preserved.", True
    ), False, False, 0)
    current_keys = read_shortcuts()
    inputs = {}
    for name, heading in (("screenshot", "Screenshot"),
                          ("files", "Open files"),
                          ("terminal", "Terminal")):
        field = Gtk.Entry()
        field.set_text(current_keys.get(name, DEFAULT_KEYS[name]))
        inputs[name] = field
        keyboard.pack_start(row(label(heading + ":"), field), False, False, 0)

    def save_keys(_button):
        def action():
            save_shortcuts({key: widget.get_text().strip()
                            for key, widget in inputs.items()})
            reload_labwc()
            return "Keyboard shortcuts saved and Labwc reconfigured."
        attempt(action)
    save_keys_button = Gtk.Button(label="Save shortcuts")
    save_keys_button.connect("clicked", save_keys)
    keyboard.pack_start(save_keys_button, False, False, 0)

    # Defaults: XDG MIME handlers are deliberately described as user-wide.
    defaults = page(notebook, "Default applications")
    defaults.pack_start(title("Default applications"), False, False, 0)
    defaults.pack_start(label(
        "These are standard XDG file and URL defaults. Changing them also "
        "affects applications in other desktop sessions, including COSMIC. "
        "Tres's Files button uses your chosen file manager.", True
    ), False, False, 0)
    combos = {}
    initial = {}
    handlers = {}
    for caption, mime in MIME_CHOICES:
        chooser = Gtk.ComboBoxText()
        available = {}
        for app in Gio.AppInfo.get_all_for_type(mime):
            app_id = app.get_id()
            if mime == "inode/directory" and _is_cosmic(app):
                # COSMIC Files relies on a different desktop's services.
                continue
            if app_id and app_id not in available:
                available[app_id] = app
        existing = Gio.AppInfo.get_default_for_type(mime, False)
        if existing and existing.get_id() and not (
            mime == "inode/directory" and _is_cosmic(existing)
        ):
            available[existing.get_id()] = existing
        for app_id, app in sorted(available.items(),
                                  key=lambda pair: pair[1].get_name().casefold()):
            chooser.append(app_id, app.get_name())
        if existing and existing.get_id() in available:
            chooser.set_active_id(existing.get_id())
        elif available:
            chooser.set_active(0)
        else:
            chooser.set_sensitive(False)
        combos[mime] = chooser
        initial[mime] = existing.get_id() if existing else None
        handlers[mime] = available
        defaults.pack_start(row(label(caption + ":"), chooser), False, False, 0)

    defaults.pack_start(label(
        "If no suitable file manager appears, install one such as Thunar "
        "(sudo apt install thunar) and reopen settings.", True
    ), False, False, 0)

    terminal = Gtk.ComboBoxText()
    terminal.append("auto", "Automatic (Foot first)")
    for name in TERMINALS:
        if shutil.which(name):
            terminal.append(name, name)
    selected_terminal = read_terminal()
    if not terminal.set_active_id(selected_terminal):
        terminal.set_active_id("auto")
    defaults.pack_start(row(label("Terminal:"), terminal), False, False, 0)

    def apply_defaults(_button):
        def action():
            changed = []
            errors = []
            for caption, mime in MIME_CHOICES:
                app_id = combos[mime].get_active_id()
                if not app_id or app_id == initial[mime]:
                    continue
                try:
                    if not handlers[mime][app_id].set_as_default_for_type(mime):
                        raise RuntimeError("The XDG service refused the change.")
                    changed.append(caption)
                    initial[mime] = app_id
                except (GLib.Error, ValueError, RuntimeError) as error:
                    errors.append(f"{caption}: {error}")
            save_terminal(terminal.get_active_id() or "auto")
            if errors:
                raise RuntimeError("; ".join(errors))
            return ("Saved defaults: " + ", ".join(changed) if changed
                    else "Default applications saved.")
        attempt(action)

    save_defaults = Gtk.Button(label="Save default applications")
    save_defaults.connect("clicked", apply_defaults)
    defaults.pack_start(save_defaults, False, False, 0)

    window.show_all()
    # CI exercises the real GTK3 widget tree under Xvfb without a compositor.
    if os.environ.get("TRES_SETTINGS_SMOKE") == "1":
        GLib.timeout_add(400, lambda: window.destroy() or False)
    Gtk.main()


if __name__ == "__main__":
    try:
        main()
    except (ImportError, ValueError) as error:
        sys.exit(f"Tres Settings requires GTK3: {error}")
