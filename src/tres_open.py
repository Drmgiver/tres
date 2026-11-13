"""Open the home folder with the user's desktop-default file manager.

Never hard-code COSMIC Files in the independent Tres session.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class FileManagerError(RuntimeError):
    pass


# Compatibility fallback when the XDG default still points to COSMIC Files.
FILE_MANAGERS = ("thunar", "nemo", "pcmanfm", "pcmanfm-qt",
                 "nautilus", "dolphin", "caja", "spacefm", "xfe")


def _is_cosmic(app) -> bool:
    try:
        descriptor = " ".join(str(value or "") for value in
                              (app.get_id(), app.get_executable(), app.get_name()))
    except (AttributeError, TypeError):
        return False
    return "cosmic" in descriptor.casefold()


def open_home() -> None:
    try:
        import gi
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio
        app = Gio.AppInfo.get_default_for_type("inode/directory", False)
        if app is not None and not _is_cosmic(app):
            files = [Gio.File.new_for_path(str(Path.home()))]
            if app.launch(files, None):
                return
    except (ImportError, ValueError) as error:
        # A non-COSMIC fallback is still available without PyGObject.
        problem = str(error)
    except Exception as error:
        problem = str(error)
    else:
        problem = "No compatible file manager set as default."

    for binary in FILE_MANAGERS:
        if shutil.which(binary):
            try:
                subprocess.Popen([binary, str(Path.home())], start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
    raise FileManagerError(
        "No compatible file manager could be opened. Install one, such as "
        "'sudo apt install thunar', and select it in Reconfigure Tres → "
        "Default applications. " + problem
    )
