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
from tres_display import DisplayError, apply_scale, output_info, parse_output_text
from tres_shortcuts import DEFAULT_KEYS, read_shortcuts, save_shortcuts
from tres_open import FILE_MANAGERS, FileManagerError, file_manager_choices, open_home, launch_fallback


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
    def test_read_enabled_outputs_on_older_wlr_randr(self, run, _which):
        # Exact text shape from older wlr-randr builds without --json.
        run.return_value.returncode = 0
        run.return_value.stdout = (
            'eDP-1 "Built-in display (eDP-1)"\n'
            '  Physical size: 286x179 mm\n'
            '  Enabled: yes\n'
            '  Modes:\n'
            '    2560x1600 px, 60.000000 Hz (preferred, current)\n'
            '  Position: 0,0\n'
            '  Transform: normal\n'
            '  Scale: 1.500000\n'
            'HDMI-A-1 "External screen"\n'
            '  Enabled: no\n'
            '  Modes:\n'
            '    1920x1080 px, 60.000000 Hz\n'
        )
        self.assertEqual(output_info(), [("eDP-1", 1.5)])
        run.assert_called_once_with(
            ["wlr-randr"], capture_output=True, text=True, timeout=6,
            check=False,
        )

    def test_parse_multiple_active_outputs_and_disabled_one(self):
        text = (
            'eDP-1 "Laptop panel"\n Enabled: yes\n Scale: 1.250000\n'
            'HDMI-A-1 "Monitor"\n Enabled: yes\n Scale: 2.000000\n'
            'DP-3 "Unplugged"\n Enabled: no\n'
        )
        self.assertEqual(
            parse_output_text(text),
            [("eDP-1", 1.25), ("HDMI-A-1", 2.0)],
        )

    def test_text_parser_handles_single_output_without_description(self):
        self.assertEqual(
            parse_output_text("eDP-1\n Enabled: yes\n Scale: 1.500000\n"),
            [("eDP-1", 1.5)],
        )

    def test_text_parser_rejects_unparseable_scale(self):
        with self.assertRaisesRegex(DisplayError, "Invalid scale"):
            parse_output_text('eDP-1 "Panel"\n Enabled: yes\n Scale: unknown\n')

    @patch("tres_display.shutil.which", return_value="/usr/bin/wlr-randr")
    @patch("tres_display.subprocess.run")
    def test_no_active_outputs_returns_clear_error(self, run, _which):
        run.return_value.returncode = 0
        run.return_value.stdout = 'DP-1 "Off"\n Enabled: no\n'
        with self.assertRaisesRegex(DisplayError, "No enabled displays"):
            output_info()

    @patch("tres_display.shutil.which", return_value="/usr/bin/wlr-randr")
    @patch("tres_display.subprocess.run")
    def test_command_failure_is_reported(self, run, _which):
        run.return_value.returncode = 1
        run.return_value.stderr = "Cannot connect to Wayland compositor"
        with self.assertRaisesRegex(DisplayError, "Cannot connect"):
            output_info()

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
    def test_settings_installer_never_launches_terminal(self):
        script = ROOT / "scripts/install-settings.sh"
        syntax = subprocess.run(
            ["bash", "-n", str(script)], capture_output=True, text=True, check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

        with TemporaryDirectory() as td:
            home = Path(td)
            bin_dir = home / ".local/bin"
            bin_dir.mkdir(parents=True)
            launched = home / "unexpected-terminal-launch"
            # An existing, Tres-managed launcher that would visibly create a
            # terminal if the installer accidentally invoked it.
            terminal = bin_dir / "tres-open-terminal"
            terminal.write_text(
                "#!/bin/sh\n# Tres-managed launcher\n"
                + "touch " + str(launched) + "\n",
                encoding="utf-8",
            )
            terminal.chmod(0o755)
            env = {**os.environ, "HOME": td}
            result = subprocess.run(
                ["bash", str(script)], env=env, capture_output=True,
                text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(launched.exists(),
                             "Installing launchers unexpectedly started a terminal")
            self.assertIn("tres_terminal.py", terminal.read_text(encoding="utf-8"))
            self.assertIn('exec /usr/bin/python3', terminal.read_text(encoding="utf-8"))

    def test_settings_installer_does_not_replace_unowned_launcher(self):
        script = ROOT / "scripts/install-settings.sh"
        with TemporaryDirectory() as td:
            home = Path(td)
            bin_dir = home / ".local/bin"
            bin_dir.mkdir(parents=True)
            terminal = bin_dir / "tres-open-terminal"
            terminal.write_text("#!/bin/sh\necho customized\n", encoding="utf-8")
            terminal.chmod(0o755)
            env = {**os.environ, "HOME": td}
            result = subprocess.run(
                ["bash", str(script)], env=env, capture_output=True,
                text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(terminal.read_text(encoding="utf-8"),
                             "#!/bin/sh\necho customized\n")

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
    class FakeApp:
        def __init__(self, app_id, name, executable, categories="", mime_types=()):
            self.app_id = app_id
            self.name = name
            self.executable = executable
            self.categories = categories
            self.mime_types = mime_types

        def get_id(self):
            return self.app_id

        def get_name(self):
            return self.name

        def get_executable(self):
            return self.executable

        def get_categories(self):
            return self.categories

        def get_supported_types(self):
            return self.mime_types

    def test_discovers_unregistered_file_managers_by_desktop_category(self):
        default = self.FakeApp("org.example.Files.desktop", "Files", "files")
        alternate = self.FakeApp(
            "org.example.AlternateFiles.desktop", "Alternate Files",
            "unlisted-file-manager", categories="Utility;FileManager;",
        )
        unrelated = self.FakeApp("org.example.Writer.desktop", "Writer", "writer",
                                 categories="Office;WordProcessor;")
        discovered = file_manager_choices(
            registered=[default],
            installed=[alternate, unrelated],
            current=default,
        )
        self.assertEqual(
            set(discovered),
            {"org.example.Files.desktop", "org.example.AlternateFiles.desktop"},
        )
        self.assertIs(discovered[alternate.get_id()], alternate)

    def test_all_folder_mime_handlers_and_default_are_selectable(self):
        unlisted = self.FakeApp("org.example.NewFiles.desktop", "New Files", "newfiles")
        folder_handler = self.FakeApp("org.example.DiskTool.desktop", "Disk Tool", "disktool",
                                      mime_types=("inode/directory",))
        registered = self.FakeApp("org.example.Folders.desktop", "Folders", "folders")
        discovered = file_manager_choices(
            [registered], [unlisted, folder_handler], unlisted,
        )
        self.assertEqual(
            set(discovered),
            {registered.get_id(), unlisted.get_id(), folder_handler.get_id()},
        )

    def test_executable_hints_are_additive_not_a_restriction(self):
        known = self.FakeApp("org.example.Thunar.desktop", "Files", "thunar")
        unknown = self.FakeApp("org.example.NewManager.desktop", "Files", "new-manager",
                               categories="FileManager;")
        selected = file_manager_choices([], [known, unknown])
        self.assertEqual(len(selected), 2)
        self.assertIn("thunar", FILE_MANAGERS)

    def test_chosen_default_is_launched_even_without_known_executable(self):
        import types
        current = self.FakeApp(
            "org.example.AlternateFiles.desktop", "Alternate Files", "my-own-manager",
        )
        opened = []
        current.launch = lambda files, context: opened.append((files, context)) or True
        gi = types.ModuleType("gi")
        gi.require_version = lambda *_args: None
        gi_repo = types.ModuleType("gi.repository")
        gi_repo.Gio = types.SimpleNamespace(
            AppInfo=types.SimpleNamespace(
                get_default_for_type=lambda content_type, supports_uri: current,
            ),
            File=types.SimpleNamespace(new_for_path=lambda path: path),
        )
        gi.repository = gi_repo
        with patch.dict(sys.modules, {"gi": gi, "gi.repository": gi_repo}):
            open_home()
        self.assertEqual(len(opened), 1)
        self.assertEqual(opened[0][0], [str(Path.home())])

    @patch("tres_open.subprocess.Popen")
    @patch("tres_open.shutil.which",
           side_effect=lambda cmd: "/usr/bin/" + cmd if cmd == "thunar" else None)
    def test_fallback_requires_explicit_choice(self, which, popen):
        with patch.dict(sys.modules, {"gi": None}):
            with self.assertRaises(FileManagerError):
                open_home()
        popen.assert_not_called()
        launch_fallback()
        self.assertEqual(popen.call_args.args[0][0], "thunar")

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
        self.assertIn('file_manager_choices(', settings)
        self.assertIn('Gio.AppInfo.get_all()', settings)

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
