#!/usr/bin/python3
"""Small native GTK3 application search dialog for the Tres left square."""
from __future__ import annotations

import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gio, Gtk, Gdk

from tres_applications import visible_applications, matching_applications, launch_application


class SearchWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Search Applications — Tres")
        self.set_default_size(440, 380)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(12)
        self.connect("destroy", Gtk.main_quit)
        self.apps = visible_applications(Gio)
        self.results = []
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(layout)
        self.entry = Gtk.SearchEntry()
        self.entry.set_placeholder_text("Search installed applications…")
        self.entry.connect("search-changed", self.refresh)
        self.entry.connect("activate", self.launch_selected)
        self.entry.connect("key-press-event", self.on_search_key)
        layout.pack_start(self.entry, False, False, 0)
        self.model = Gtk.ListStore(str, object)
        self.listing = Gtk.TreeView(model=self.model)
        self.listing.set_headers_visible(False)
        self.listing.set_search_column(-1)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Application", renderer, text=0)
        self.listing.append_column(column)
        self.listing.connect("row-activated", self.on_row_activated)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.listing)
        layout.pack_start(scroll, True, True, 0)
        self.status = Gtk.Label()
        self.status.set_xalign(0)
        layout.pack_start(self.status, False, False, 0)
        self.refresh()
        self.show_all()
        self.entry.grab_focus()

    def refresh(self, *_args):
        matches = matching_applications(self.apps, self.entry.get_text())
        self.model.clear()
        for app in matches:
            self.model.append([app.get_name(), app])
        self.status.set_text(f"{len(matches)} application(s)")
        if matches:
            self.listing.set_cursor(Gtk.TreePath.new_from_indices([0]))

    def on_search_key(self, _entry, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if event.keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            selection = self.listing.get_selection()
            model, tree_iter = selection.get_selected()
            current = model.get_path(tree_iter).get_indices()[0] if tree_iter else 0
            step = 1 if event.keyval == Gdk.KEY_Down else -1
            if len(model):
                self.listing.set_cursor(Gtk.TreePath.new_from_indices(
                    [max(0, min(len(model) - 1, current + step))]))
            return True
        return False

    def launch_selected(self, *_args):
        model, tree_iter = self.listing.get_selection().get_selected()
        if tree_iter:
            self.launch_app(model[tree_iter][1])

    def on_row_activated(self, _view, path, _column):
        self.launch_app(self.model[path][1])

    def launch_app(self, app):
        if launch_application(app):
            self.close()


def main():
    SearchWindow()
    Gtk.main()


if __name__ == "__main__":
    main()
