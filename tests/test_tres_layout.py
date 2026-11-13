"""Exercise Tres stacking choices without launching a Wayland compositor."""
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tres_layout import DEFAULT_MODE, MODES, mode_path, read_mode, save_mode  # noqa: E402


class TestTresLayout(unittest.TestCase):
    def test_default_and_invalid_file_fall_back_to_under(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "panel-mode"
            self.assertEqual(read_mode(path), "under")
            path.write_text("unknown\n", encoding="utf-8")
            self.assertEqual(read_mode(path), "under")

    def test_all_three_modes_persist(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "tres" / "panel-mode"
            for mode in MODES:
                save_mode(mode, path)
                self.assertEqual(read_mode(path), mode)
            with self.assertRaises(ValueError):
                save_mode("fullscreen", path)
            self.assertEqual(read_mode(path), "reserved")

    def test_settings_are_tres_only(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": td}):
                self.assertEqual(mode_path(), pathlib.Path(td) / "tres" / "panel-mode")
                self.assertEqual(DEFAULT_MODE, "under")

    def test_right_click_menu_preserves_labwc_actions(self):
        for relative in ("scripts/menu.xml", "packaging/deb/menu.xml"):
            menu = ElementTree.parse(ROOT / relative).getroot()
            root = menu.find("./menu[@id='root-menu']")
            self.assertIsNotNone(root)
            actions = {
                item.get("label"): item.find("action")
                for item in root.findall("item")
            }
            self.assertEqual(actions["Reconfigure Tres"].get("name"), "Execute")
            self.assertEqual(actions["Reconfigure"].get("name"), "Reconfigure")
            self.assertEqual(actions["Exit"].get("name"), "Exit")
            cmd = actions["Reconfigure Tres"].get("command")
            if cmd is None:
                cmd = actions["Reconfigure Tres"].findtext("command")
            self.assertIn("tres-config", cmd)


if __name__ == "__main__":
    unittest.main()
