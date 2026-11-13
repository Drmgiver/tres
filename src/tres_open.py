"""Open the user's home folder with a supported freedesktop file manager."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class FileManagerError(RuntimeError):
    pass


# Known file managers are used only as a *fallback* when no default opens.
# Never use this tuple to limit the user's selectable installed applications.
FILE_MANAGERS = ("thunar", "nemo", "pcmanfm", "pcmanfm-qt",
                 "nautilus", "dolphin", "caja", "spacefm", "xfe")


def file_manager_choices(registered, installed, current=None) -> dict:
    """Discover launchable desktop file managers without a vendor allowlist.

    The XDG folder handler list can omit file managers whose desktop entries
    advertise the FileManager category but no inode/directory MIME type.
    Include both sources and the current handler so users can select any of
    their installed graphical file managers.
    """
    choices = {}

    def add(app) -> None:
        if app is None:
            return
        try:
            app_id = app.get_id()
        except (AttributeError, TypeError):
            return
        if app_id:
            choices.setdefault(app_id, app)

    for app in registered or ():
        add(app)
    add(current)
    for app in installed or ():
        try:
            categories = set((app.get_categories() or "").split(";"))
        except (AttributeError, TypeError):
            categories = set()
        try:
            supported_types = set(app.get_supported_types() or ())
        except (AttributeError, TypeError):
            supported_types = set()
        try:
            executable = Path(str(app.get_executable() or "")).name
        except (AttributeError, TypeError):
            executable = ""
        if ("FileManager" in categories or "inode/directory" in supported_types
                or executable in FILE_MANAGERS):
            add(app)
    return choices


def open_home() -> None:
    problem = "The selected file manager could not be opened."
    try:
        import gi
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio
        app = Gio.AppInfo.get_default_for_type("inode/directory", False)
        if app is not None:
            # Honor the user's XDG preference even if the desktop entry is
            # outside the small fallback list. Do not filter by desktop origin.
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
        "No file manager could be opened. Install one, such as "
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
