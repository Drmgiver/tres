"""Open the user's home folder with a supported freedesktop file manager."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class FileManagerError(RuntimeError):
    pass


# Compatible standalone file managers. This list is intentionally independent
# of any particular desktop environment or vendor.
FILE_MANAGERS = ("thunar", "nemo", "pcmanfm", "pcmanfm-qt",
                 "nautilus", "dolphin", "caja", "spacefm", "xfe")


def is_supported_file_manager(app) -> bool:
    """Recognize the executable, not the origin desktop's brand or app name."""
    try:
        executable = str(app.get_executable() or "").strip()
    except (AttributeError, TypeError):
        return False
    return Path(executable).name in FILE_MANAGERS


def open_home() -> None:
    problem = "No supported file manager is set as default."
    try:
        import gi
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio
        app = Gio.AppInfo.get_default_for_type("inode/directory", False)
        if app is not None and is_supported_file_manager(app):
            files = [Gio.File.new_for_path(str(Path.home()))]
            if app.launch(files, None):
                return
    except Exception as error:
        problem = str(error)

    for binary in FILE_MANAGERS:
        if shutil.which(binary):
            try:
                subprocess.Popen([binary, str(Path.home())], start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
    raise FileManagerError(
        "No supported file manager could be opened. Install one, such as "
        "'sudo apt install thunar', and select it in Reconfigure Tres → "
        "Default applications. " + problem
    )


def main() -> None:
    try:
        open_home()
    except FileManagerError as error:
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
            dialog = Gtk.MessageDialog(
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE,
                text="Tres cannot open Files",
            )
            dialog.format_secondary_text(str(error)[:600])
            dialog.run()
            dialog.destroy()
        except (ImportError, ValueError):
            import sys
            print(f"Tres Files: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
