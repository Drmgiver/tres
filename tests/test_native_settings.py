"""Regression tests for native Tres appearance, scaling, shortcuts, and Files."""
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import os
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tres_preferences import (DEFAULT_APPEARANCE, read_appearance, save_appearance,
                              read_terminal, save_terminal)
from tres_display import DisplayError, apply_scale, output_info
from tres_shortcuts import DEFAULT_KEYS, read_shortcuts, save_shortcuts
from tres_open import FILE_MANAGERS, FileManagerError, open_home


class PreferencesTests(TestCase):
    def test_default_appearance_and_colors_persist(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "appearance.json"
            self.assertEqual(read_appearance(p), DEFAULT_APPEARANCE)
            updated = {**DEFAULT_APPEARANCE, "square_color": "#Ff0000",
                       "wallpaper_color": "#112233", "square_size": 23}
            save_appearance(updated, p)
            self.assertEqual(read_appearance(p)["square_color"], "#ff0000")
            self.assertEqual(read_appearance(p)["square_size"], 23)
            self.assertEqual(read_appearance(p)["wallpaper_color"], "#112233")
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)

    def test_invalid_colors_or_sizes_do_not_save(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "appearance.json"
            for bad in ("red;gtk.css", "red", "#12", "#gg1122"):
                with self.assertRaises(ValueError):
                    save_appearance({**DEFAULT_APPEARANCE, "square_color": bad}, p)
            with self.assertRaises(ValueError):
                save_appearance({**DEFAULT_APPEARANCE, "square_size": 500}, p)
            self.assertFalse(p.exists())

    def test_terminal_whitelist_and_persistence(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "terminal"
            self.assertEqual(read_terminal(p), "auto")
            save_terminal("terminator", p)
            self.assertEqual(read_terminal(p), "terminator")
            with self.assertRaises(ValueError):
                save_terminal("rm -rf ~", p)
            self.assertEqual(read_terminal(p), "terminator")


class DisplayTests(TestCase):
    @patch("tres_display.shutil.which", return_value="/usr/bin/wlr-randr")
    @patch("tres_display.subprocess.run")
    def test_read_enabled_outputs(self, run, _which):
        run.return_value.returncode = 0
        run.return_value.stdout = (
            '[{"name":"eDP-1","scale":1.5,"enabled":true},'
            '{"name":"HDMI-A-1","scale":1,"enabled":false}]'
        )
        self.assertEqual(output_info(), [("eDP-1", 1.5)])
        self.assertEqual(run.call_args.args[0], ["wlr-randr", "--json"])

    @patch("tres_display.shutil.which", return_value="/usr/bin/wlr-randr")
    @patch("tres_display.subprocess.run")
    def test_scale_preserves_user_autostart_and_updates_existing_block(self, run, _which):
        run.return_value.returncode = 0
        with TemporaryDirectory() as td:
            p = Path(td) / "autostart"
            p.write_text(
                "#!/bin/sh\ncustom-wallpaper &\n"
                "# BEGIN TRES DISPLAY SCALE\n"
                "(sleep 1; wlr-randr --output eDP-1 --scale 1.5) &\n"
                "# END TRES DISPLAY SCALE\n", encoding="utf-8",
            )
            apply_scale("eDP-1", 2, p)
            updated = p.read_text()
            self.assertIn("custom-wallpaper &", updated)
            self.assertEqual(updated.count("# BEGIN TRES DISPLAY SCALE"), 1)
            self.assertIn("wlr-randr --output eDP-1 --scale 2", updated)
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0],
                             ["wlr-randr", "--output", "eDP-1", "--scale", "2"])

    @patch("tres_display.shutil.which", return_value="/usr/bin/wlr-randr")
    @patch("tres_display.subprocess.run")
    def test_failed_wlr_randr_does_not_touch_config(self, run, _which):
        run.return_value.returncode = 1
        run.return_value.stderr = "Compositor refused scale"
        with TemporaryDirectory() as td:
            p = Path(td) / "autostart"
            p.write_text("#!/bin/sh\nunchanged\n")
            with self.assertRaises(DisplayError):
                apply_scale("eDP-1", 1.5, p)
            self.assertEqual(p.read_text(), "#!/bin/sh\nunchanged\n")

    def test_invalid_display_identifier_never_runs_command(self):
        with self.assertRaises(ValueError):
            apply_scale("--output", 2)
        with self.assertRaises(ValueError):
            apply_scale("eDP-1", 99)


class ShortcutsTests(TestCase):
    def test_keyboard_keeps_existing_custom_bindings_and_defaults(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "labwc/rc.xml"
            p.parent.mkdir()
            original = ('<labwc_config><keyboard><default />'
                        '<keybind key="A-F10"><action name="Close" /></keybind>'
                        '</keyboard><theme><name>MyTheme</name></theme></labwc_config>')
            p.write_text(original)
            keys = {"screenshot": "Print", "files": "W-e", "terminal": "W-Return"}
            save_shortcuts(keys, p)
            result = p.read_text()
            ET.fromstring(result)
            self.assertIn('key="A-F10"', result)
            self.assertIn("<name>MyTheme</name>", result)
            self.assertIn("<default />", result)
            self.assertEqual(read_shortcuts(p), keys)
            self.assertEqual(result.count("BEGIN TRES SHORTCUTS"), 1)
            save_shortcuts({"screenshot": "W-s", "files": "W-f",
                            "terminal": "W-Return"}, p)
            result = p.read_text()
            self.assertEqual(result.count("BEGIN TRES SHORTCUTS"), 1)
            self.assertNotIn('key="Print"', result)
            self.assertIn('key="A-F10"', result)

    def test_shortcut_validation_rejects_duplicates_and_injection(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "rc.xml"
            with self.assertRaises(ValueError):
                save_shortcuts({"screenshot": "W-e", "files": "W-e",
                                "terminal": "W-Return"}, p)
            with self.assertRaises(ValueError):
                save_shortcuts({"screenshot": 'W-e" /> <action name="Exit"',
                                "files": "W-f", "terminal": "W-Return"}, p)
            self.assertFalse(p.exists())

    def test_invalid_existing_rc_xml_is_preserved(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "rc.xml"
            p.write_text("<labwc_config><keyboard>")
            with self.assertRaises(ValueError):
                save_shortcuts(DEFAULT_KEYS, p)
            self.assertEqual(p.read_text(), "<labwc_config><keyboard>")


class UpgradeTests(TestCase):
    def test_shell_updater_keeps_existing_scale_and_custom_configuration(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            config = home / ".config/tres/labwc"
            config.mkdir(parents=True)
            previous = ('#!/bin/sh\n'
                        'if command -v swaybg >/dev/null 2>&1; then\n'
                        "    swaybg -c '#141414' >/dev/null 2>&1 &\n"
                        'fi\n'
                        '# BEGIN TRES DISPLAY SCALE\n'
                        '(sleep 1; wlr-randr --output eDP-1 --scale 1.5) &\n'
                        '# END TRES DISPLAY SCALE\n'
                        'custom-session-hook &\n')
            autostart = config / "autostart"
            autostart.write_text(previous, encoding="utf-8")
            env = {**os.environ, "HOME": td}
            script = ROOT / "scripts/install-settings.sh"
            for _ in range(2):  # idempotent, not just one successful run
                result = subprocess.run(
                    ["bash", str(script)], env=env, capture_output=True,
                    text=True, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            updated = autostart.read_text(encoding="utf-8")
            self.assertIn('"$HOME/.local/bin/tres-wallpaper"', updated)
            self.assertIn("--output eDP-1 --scale 1.5", updated)
            self.assertIn("custom-session-hook &", updated)
            self.assertEqual(updated.count("tres-wallpaper"), 1)
            self.assertEqual((config / "autostart.before-tres-wallpaper").read_text(),
                             previous)
            self.assertTrue((home / ".local/bin/tres-open-files").exists())
            self.assertTrue((home / ".local/bin/tres-wallpaper").exists())
            self.assertTrue((home / ".local/bin/tres-open-terminal").exists())


class FileManagerTests(TestCase):
    @patch("tres_open.subprocess.Popen")
    @patch("tres_open.shutil.which", side_effect=lambda cmd: "/usr/bin/" + cmd if cmd == "thunar" else None)
    def test_unsupported_default_falls_back_to_standalone_manager(self, which, popen):
        class Bad:
            def get_id(self): return "org.example.DesktopBoundFiles.desktop"
            def get_executable(self): return "desktop-bound-files"
            def get_name(self): return "Desktop Bound Files"
        # Simulate missing GI on the build machine: use an independent fallback.
        with patch.dict(sys.modules, {"gi": None}):
            open_home()
        self.assertEqual(popen.call_args.args[0][0], "thunar")
        self.assertNotIn("desktop-bound-files", FILE_MANAGERS)

    def test_right_square_uses_default_file_manager(self):
        panel = (ROOT / "src/tres_panel.py").read_text()
        self.assertNotIn('("Files", (', panel)
        self.assertIn("tres-open-files", panel)
        self.assertIn("open_terminal", panel)

    def test_defaults_do_not_change_unselected_file_handlers(self):
        settings = (ROOT / "src/tres_config.py").read_text()
        self.assertIn('chooser.append("__keep__"', settings)
        self.assertIn('app_id == "__keep__"', settings)
        self.assertIn('"x-scheme-handler/http"', settings)
        self.assertIn('"text/html"', settings)
        self.assertIn('not is_supported_file_manager(existing)', settings)

    def test_default_files_helper_is_packaged_and_installed(self):
        install = (ROOT / "debian/tres.install").read_text()
        self.assertIn("src/tres_open.py usr/share/tres", install)
        self.assertIn("packaging/deb/tres-open-files usr/bin", install)
        self.assertIn("scripts/install-settings.sh",
                      (ROOT / "scripts/update-panel.sh").read_text())
        self.assertIn("packaging/deb/tres-open-terminal usr/bin", install)


if __name__ == "__main__":
    import unittest
    unittest.main()
