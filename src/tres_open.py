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
    """Launch the chosen XDG handler, never silently substitute another app."""
    try:
        import gi
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio
        app = Gio.AppInfo.get_default_for_type("inode/directory", False)
        if app is None:
            raise FileManagerError("No default folder application is configured.")
        files = [Gio.File.new_for_path(str(Path.home()))]
        if not app.launch(files, None):
            raise FileManagerError(f"Could not launch {app.get_name()}.")
    except FileManagerError:
        raise
    except Exception as error:
        raise FileManagerError(f"Unable to open the selected file manager: {error}") from error


def launch_fallback() -> None:
    """Explicit user-approved alternative to the selected file manager."""
    for binary in FILE_MANAGERS:
        if shutil.which(binary):
            try:
                subprocess.Popen([binary, str(Path.home())], start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
    raise FileManagerError(
        "No alternative file manager could be opened. "
        "Select one in Reconfigure Tres → Default applications."
    )


def main() -> None:
    try:
        open_home()
        return
    except FileManagerError as error:
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
            dialog = Gtk.MessageDialog(
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Tres could not open the selected file manager",
            )
            dialog.format_secondary_text(str(error)[:500] +
                                         "\nTry another installed file manager?")
            choice = dialog.run()
            dialog.destroy()
            if choice == Gtk.ResponseType.YES:
                try:
                    launch_fallback()
                    return
                except FileManagerError as fallback_error:
                    problem = Gtk.MessageDialog(
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.CLOSE,
                        text="Unable to open Files",
                    )
                    problem.format_secondary_text(str(fallback_error))
                    problem.run()
                    problem.destroy()
        except (ImportError, ValueError):
            import sys
            print(f"Tres Files: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
