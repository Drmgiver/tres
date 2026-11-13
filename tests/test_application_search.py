"""Tests for search filtering, menu placement and launch compatibility."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tres_applications import matching_applications, visible_applications, launch_application


class FakeApp:
    def __init__(self, name, app_id, description="", show=True):
        self.name, self.app_id, self.description, self.show = name, app_id, description, show
        self.launch = Mock()

    def get_name(self):
        return self.name

    def get_display_name(self):
        return self.name

    def get_id(self):
        return self.app_id

    def get_description(self):
        return self.description

    def should_show(self):
        return self.show


class SearchTests(unittest.TestCase):
    def test_hidden_applications_are_not_listed(self):
        apps = [FakeApp("Visible", "visible.desktop"),
                FakeApp("Hidden", "hidden.desktop", show=False)]
        gio = SimpleNamespace(AppInfo=SimpleNamespace(get_all=lambda: apps))
        self.assertEqual(visible_applications(gio), [apps[0]])

    def test_case_insensitive_and_multiterm_search(self):
        apps = [FakeApp("Image Editor", "editor.desktop", "Paint images"),
                FakeApp("Terminal", "terminal.desktop", "Run commands")]
        self.assertEqual(matching_applications(apps, "IMAGE paint"), [apps[0]])
        self.assertEqual(matching_applications(apps, "TERMINAL"), [apps[1]])
        self.assertEqual(matching_applications(apps, "missing"), [])
        self.assertEqual(len(matching_applications(apps, "")), 2)

    def test_regular_app_uses_gio_launch(self):
        app = FakeApp("Terminal", "terminal.desktop")
        self.assertTrue(launch_application(app))
        app.launch.assert_called_once_with([], None)

    def test_synaptic_does_not_bypass_wrapper(self):
        app = FakeApp("Synaptic", "synaptic.desktop")
        with patch("tres_applications.Path.home", return_value=Path("/nonexistent/tres-search-test")):
            with patch("tres_applications.Path.is_file", return_value=False):
                self.assertFalse(launch_application(app))
        app.launch.assert_not_called()

    def test_search_appears_at_top_of_left_menu(self):
        tree = ast.parse((ROOT / "src/tres_panel.py").read_text())
        tres = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Tres")
        menu = next(n for n in tres.body if isinstance(n, ast.FunctionDef)
                    and n.name == "applications_menu")
        strings = [n.value for n in ast.walk(menu)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertIn("Search Applications…", strings)
        self.assertIn("/usr/bin/tres-search", strings)

    def test_gtk_search_dialog_source_compiles(self):
        ast.parse((ROOT / "src/tres_search.py").read_text())


if __name__ == "__main__":
    unittest.main()
