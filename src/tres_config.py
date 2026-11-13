#!/usr/bin/python3
"""The small stacking-dialog opened by Tres's desktop right-click menu."""
from __future__ import annotations

import sys

from tres_layout import MODES, read_mode, save_mode

CHOICES = (
    ("under", "Under", "Windows may cover the three squares."),
    ("over", "Over", "The three squares stay above normal windows."),
    ("reserved", "Space reserved", "Maximized windows leave room at the top."),
)


def main() -> None:
    import gi
    # Match the panel's explicit GTK3 bootstrap (COSMIC also provides GTK4).
    gi.require_version("Gdk", "3.0")
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    dialog = Gtk.Dialog(title="Reconfigure Tres")
    dialog.set_default_size(420, 220)
    dialog.set_border_width(12)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Apply", Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.OK)

    content = dialog.get_content_area()
    content.set_spacing(10)
    intro = Gtk.Label(label="Choose how Tres's three squares interact with windows:")
    intro.set_xalign(0)
    content.pack_start(intro, False, False, 0)

    buttons = {}
    group = None
    for key, label, description in CHOICES:
        button = Gtk.RadioButton.new_with_label_from_widget(group, label) if group else (
            Gtk.RadioButton.new_with_label(None, label)
        )
        if group is None:
            group = button
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.pack_start(button, False, False, 0)
        detail = Gtk.Label(label=description)
        detail.set_xalign(0)
        detail.set_margin_start(24)
        box.pack_start(detail, False, False, 0)
        content.pack_start(box, False, False, 0)
        buttons[key] = button

    buttons[read_mode()].set_active(True)
    dialog.show_all()

    if dialog.run() == Gtk.ResponseType.OK:
        chosen = next((mode for mode in MODES if buttons[mode].get_active()), None)
        if chosen:
            try:
                save_mode(chosen)
            except OSError as error:
                problem = Gtk.MessageDialog(
                    transient_for=dialog,
                    flags=Gtk.DialogFlags.MODAL,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CLOSE,
                    text="Tres could not save that setting",
                )
                problem.format_secondary_text(str(error))
                problem.run()
                problem.destroy()
    dialog.destroy()


if __name__ == "__main__":
    try:
        main()
    except (ImportError, ValueError) as error:
        sys.exit(f"Tres configuration dialog requires GTK3: {error}")
