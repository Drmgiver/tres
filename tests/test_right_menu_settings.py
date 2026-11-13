"""Right square must open Tres settings, not a COSMIC-only settings panel."""
import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "tres_panel.py"


class TestRightMenuSettings(unittest.TestCase):
    @staticmethod
    def menu_and_launcher():
        # Isolate the actual GTK menu builder without importing GI or Wayland.
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        panel = next(node for node in tree.body
                     if isinstance(node, ast.ClassDef) and node.name == "Tres")
        applets = next(node for node in panel.body
                       if isinstance(node, ast.FunctionDef)
                       and node.name == "applets_menu")
        mock_spawn = Mock(return_value=True)
        fake_gtk = SimpleNamespace(Menu=lambda: [])

        class FakePanel:
            @staticmethod
            def ask_exit():
                pass

            @staticmethod
            def item(name, callback=None):
                return (name, callback)

            @staticmethod
            def separator():
                return ("separator", None)

            @staticmethod
            def submenu(name, rows):
                return (name, rows)

        fake_gi = {
            "Gtk": fake_gtk,
            "datetime": datetime,
            "battery_label": lambda: "Battery: 75%",
            "shutil": SimpleNamespace(which=lambda _: None),
            "spawn_first": mock_spawn,
            "Path": Path,
        }
        temp = ast.Module(body=[ast.ClassDef(
            name="AppletsOnlyPanel", bases=[], keywords=[], body=[applets],
            decorator_list=[])], type_ignores=[])
        exec(compile(ast.fix_missing_locations(temp), str(SOURCE), "exec"), fake_gi)
        class Host(fake_gi["AppletsOnlyPanel"], FakePanel):
            pass
        host = Host()
        menu = host.applets_menu()
        return menu, mock_spawn

    def test_tres_settings_launcher_exists_and_is_reachable(self):
        menu, launcher = self.menu_and_launcher()
        actions = {label: callback for label, callback in menu}
        self.assertIn("Reconfigure Tres…", actions)
        self.assertNotIn("System settings", actions)
        self.assertIsNotNone(actions["Reconfigure Tres…"])
        actions["Reconfigure Tres…"]()
        self.assertEqual(launcher.call_count, 1)
        candidates = launcher.call_args.args
        self.assertTrue(str(candidates[0][0]).endswith("/.local/bin/tres-config"))
        self.assertEqual(candidates[1], ("/usr/bin/tres-config",))

    def test_existing_power_and_audio_controls_remain(self):
        menu, _ = self.menu_and_launcher()
        actions = {label: callback for label, callback in menu}
        self.assertIn("Audio", actions)
        self.assertIn("Exit Tres session…", actions)
        self.assertIn("Restart computer…", actions)
        self.assertIn("Shut down computer…", actions)

    def test_no_cosmic_settings_launcher_in_right_menu(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        panel = next(node for node in tree.body
                     if isinstance(node, ast.ClassDef) and node.name == "Tres")
        applets = next(node for node in panel.body
                       if isinstance(node, ast.FunctionDef)
                       and node.name == "applets_menu")
        strings = [
            node.value for node in ast.walk(applets)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        self.assertNotIn("cosmic-settings", strings)


if __name__ == "__main__":
    unittest.main()
