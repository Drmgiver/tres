"""Protect the GTK3 bootstrap from accidentally selecting GDK4 on COSMIC."""
import ast
import pathlib
import sys
import types
import unittest
from unittest.mock import patch


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "src" / "tres_panel.py"


class GtkImportTests(unittest.TestCase):
    def test_gtk_imports_explicitly_pin_gdk3_first(self):
        # Extract only setup_gi so this test doesn't need a graphical desktop,
        # a Wayland socket, or PyGObject installed on the CI machine.
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == "setup_gi")
        isolated = ast.Module(body=[function], type_ignores=[])
        namespace = {}
        exec(compile(isolated, str(SOURCE), "exec"), namespace)

        seen = []
        fake_gi = types.ModuleType("gi")
        fake_gi.__path__ = []
        fake_gi.require_version = lambda name, version: seen.append((name, version))
        fake_repo = types.ModuleType("gi.repository")
        expected_modules = [object() for _ in range(4)]
        for name, module in zip(("Gdk", "Gio", "Gtk", "GtkLayerShell"),
                                expected_modules):
            setattr(fake_repo, name, module)
        fake_gi.repository = fake_repo

        with patch.dict(sys.modules, {"gi": fake_gi, "gi.repository": fake_repo}):
            imported = namespace["setup_gi"]()

        self.assertEqual(seen, [
            ("Gdk", "3.0"),
            ("Gtk", "3.0"),
            ("GtkLayerShell", "0.1"),
        ])
        self.assertEqual(list(imported), expected_modules)

    def test_diagnostic_checks_same_gdk3_version(self):
        diagnostic = (SOURCE.parents[1] / "scripts" / "diagnose.sh").read_text()
        self.assertIn("gi.require_version('Gdk', '3.0')", diagnostic)
        self.assertIn("from gi.repository import Gdk, Gio, Gtk, GtkLayerShell",
                      diagnostic)


if __name__ == "__main__":
    unittest.main()
