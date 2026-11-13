"""Shared application discovery and launch behavior for Tres menus and search."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def visible_applications(Gio):
    """Only applications that are normally visible in the desktop menu."""
    result = []
    for app in Gio.AppInfo.get_all():
        try:
            if app.should_show() and app.get_name():
                result.append(app)
        except Exception:
            continue
    return result


def matching_applications(apps, query: str):
    """Case-insensitive search against displayed names, IDs and descriptions."""
    words = query.casefold().split()
    if not words:
        return sorted(apps, key=lambda app: app.get_name().casefold())
    matches = []
    for app in apps:
        try:
            search_text = " ".join(filter(None, (
                app.get_name(), app.get_display_name(), app.get_id(),
                app.get_description(),
            ))).casefold()
            if all(word in search_text for word in words):
                matches.append(app)
        except Exception:
            continue
    return sorted(matches, key=lambda app: app.get_name().casefold())


def launch_application(app):
    """Honor Synaptic's Tres-specific XWayland wrapper; use Gio for other apps."""
    try:
        desktop_id = (app.get_id() or "").casefold()
        if desktop_id in ("synaptic.desktop", "synaptic-pkexec.desktop"):
            for launcher in (Path.home() / ".local/bin/tres-synaptic",
                             Path("/usr/bin/tres-synaptic")):
                if launcher.is_file() and launcher.stat().st_mode & 0o111:
                    subprocess.Popen([str(launcher)], start_new_session=True,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
            # Never bypass the required wrapper by starting unpatched Synaptic.
            print("Tres: Synaptic compatibility launcher is not installed.", file=sys.stderr)
            return False
        app.launch([], None)
        return True
    except Exception as error:
        print(f"Tres: could not launch {app.get_name()}: {error}", file=sys.stderr)
        return False
