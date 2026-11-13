#!/usr/bin/python3
"""Tres Screenshot: minimal GTK3 interface to Grim and Slurp on Wayland."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from tres_capture import CaptureCancelled, CaptureError, capture


def main() -> None:
    import gi
    gi.require_version("Gdk", "3.0")
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk

    class ScreenshotDialog:
        def __init__(self):
            self.dialog = Gtk.Dialog(title="Tres Screenshot")
            self.dialog.set_default_size(370, 185)
            self.dialog.set_border_width(12)
            self.dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            self.dialog.add_button("Take Screenshot", Gtk.ResponseType.OK)
            self.dialog.set_default_response(Gtk.ResponseType.OK)
            self.dialog.connect("response", self.on_response)

            area = self.dialog.get_content_area()
            area.set_spacing(10)
            label = Gtk.Label(label="Capture:")
            label.set_xalign(0)
            area.pack_start(label, False, False, 0)

            self.full = Gtk.RadioButton.new_with_label(None, "Entire screen")
            self.region = Gtk.RadioButton.new_with_label_from_widget(
                self.full, "Select an area"
            )
            area.pack_start(self.full, False, False, 0)
            area.pack_start(self.region, False, False, 0)

            line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            line.pack_start(Gtk.Label(label="Delay before capture:"), False, False, 0)
            self.delay = Gtk.ComboBoxText()
            for value in ("0", "3", "5"):
                self.delay.append_text(f"{value} seconds")
            self.delay.set_active(0)
            line.pack_start(self.delay, False, False, 0)
            area.pack_start(line, False, False, 0)
            self.dialog.show_all()

        def error(self, message):
            problem = Gtk.MessageDialog(
                transient_for=self.dialog,
                flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE,
                text="Unable to capture screenshot",
            )
            problem.format_secondary_text(str(message)[:600])
            problem.run()
            problem.destroy()

        def on_response(self, _dialog, response):
            if response != Gtk.ResponseType.OK:
                self.dialog.destroy()
                Gtk.main_quit()
                return
            chooser = Gtk.FileChooserDialog(
                title="Save Screenshot As",
                transient_for=self.dialog,
                action=Gtk.FileChooserAction.SAVE,
            )
            chooser.add_button("Cancel", Gtk.ResponseType.CANCEL)
            chooser.add_button("Save", Gtk.ResponseType.OK)
            chooser.set_do_overwrite_confirmation(True)
            folder = Path.home() / "Pictures"
            if not folder.is_dir():
                folder = Path.home()
            chooser.set_current_folder(str(folder))
            chooser.set_current_name(
                "Screenshot-" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
            )
            selection = chooser.run()
            name = chooser.get_filename() if selection == Gtk.ResponseType.OK else None
            chooser.destroy()
            if not name:
                return
            destination = Path(name)
            if destination.suffix.lower() != ".png":
                # Do not silently produce JPEG or unnamed data from a PNG tool.
                destination = destination.with_name(destination.name + ".png")
                if destination.exists():
                    self.error(f"The file already exists: {destination}. Please choose another name.")
                    return

            delay_seconds = (0, 3, 5)[max(0, self.delay.get_active())]
            selected_area = self.region.get_active()
            # Hide both the dialog and file chooser before Grim/Slurp run.
            self.dialog.hide()
            GLib.timeout_add(
                delay_seconds * 1000 + 400,
                self.do_capture, destination, selected_area,
            )

        def do_capture(self, destination, selected_area):
            try:
                capture(destination, select_region=selected_area)
            except CaptureCancelled:
                # Escape on Slurp restores the dialog rather than making a file.
                self.dialog.show_all()
            except CaptureError as error:
                self.dialog.show_all()
                self.error(error)
            else:
                self.dialog.destroy()
                Gtk.main_quit()
            return False

    if not os.environ.get("WAYLAND_DISPLAY"):
        sys.exit("Tres Screenshot requires a Wayland session.")
    ScreenshotDialog()
    Gtk.main()


if __name__ == "__main__":
    try:
        main()
    except (ImportError, ValueError) as error:
        sys.exit(f"Tres Screenshot requires GTK3: {error}")
