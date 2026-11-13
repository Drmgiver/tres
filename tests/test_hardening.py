"""Regression checks for Tres hardening and desktop service integration."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import os
import subprocess
import sys
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tres_audio import AudioError, audio_backend, change_volume
from tres_display import DisplayError, apply_scale, saved_scales
from tres_menu import add_restart_action
from tres_shortcuts import DEFAULT_KEYS, read_shortcuts


class DisplayPersistenceTests(TestCase):
    @patch("tres_display.shutil.which", return_value="/usr/bin/wlr-randr")
    @patch("tres_display.subprocess.run")
    def test_two_outputs_survive_individual_updates(self, run, _which):
        run.return_value.returncode = 0
        with TemporaryDirectory() as td:
            path = Path(td) / "autostart"
            path.write_text("#!/bin/sh\ncustom-start &\n")
            apply_scale("eDP-1", 1.5, path)
            apply_scale("HDMI-A-1", 1.25, path)
            self.assertEqual(
                saved_scales(path.read_text()),
                {"eDP-1": 1.5, "HDMI-A-1": 1.25},
            )
            self.assertIn("custom-start &", path.read_text())
            self.assertEqual(path.read_text().count("# BEGIN TRES DISPLAY SCALE"), 1)
            self.assertEqual(run.call_count, 2)
            apply_scale("eDP-1", 2.0, path)
            self.assertEqual(
                saved_scales(path.read_text()),
                {"eDP-1": 2.0, "HDMI-A-1": 1.25},
            )

    @patch("tres_display.shutil.which", return_value="/usr/bin/wlr-randr")
    @patch("tres_display.subprocess.run")
    def test_custom_scale_code_never_discarded(self, run, _which):
        with TemporaryDirectory() as td:
            path = Path(td) / "autostart"
            original = ("#!/bin/sh\n# BEGIN TRES DISPLAY SCALE\n"
                        "my-special-monitor-command &\n"
                        "# END TRES DISPLAY SCALE\n")
            path.write_text(original)
            with self.assertRaises(DisplayError):
                apply_scale("eDP-1", 1.5, path)
            self.assertEqual(path.read_text(), original)
            run.assert_not_called()


class ShortcutsTests(TestCase):
    def test_empty_not_fake_default_when_no_binding_configured(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "rc.xml"
            self.assertEqual(read_shortcuts(path),
                             {name: "" for name in DEFAULT_KEYS})
            path.write_text('<labwc_config><keyboard /></labwc_config>')
            self.assertEqual(read_shortcuts(path),
                             {name: "" for name in DEFAULT_KEYS})


class AudioTests(TestCase):
    @patch("tres_audio.shutil.which", side_effect=lambda binary: binary if binary == "wpctl" else None)
    @patch("tres_audio.subprocess.run")
    def test_wpctl_volume_and_mute(self, run, _which):
        run.return_value.returncode = 0
        self.assertEqual(audio_backend(), "wpctl")
        change_volume("up")
        self.assertEqual(
            run.call_args.args[0],
            ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+"],
        )
        change_volume("mute")
        self.assertEqual(
            run.call_args.args[0],
            ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"],
        )

    @patch("tres_audio.shutil.which", side_effect=lambda binary: binary if binary == "pactl" else None)
    @patch("tres_audio.subprocess.run")
    def test_pactl_fallback_volume(self, run, _which):
        run.return_value.returncode = 0
        change_volume("down")
        self.assertEqual(run.call_args.args[0],
                         ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"])

    @patch("tres_audio.shutil.which", return_value=None)
    def test_audio_missing_is_reported(self, _which):
        with self.assertRaises(AudioError):
            change_volume("up")

    @patch("tres_audio.shutil.which", return_value="/usr/bin/wpctl")
    @patch("tres_audio.subprocess.run")
    def test_audio_server_failure_is_reported(self, run, _which):
        run.return_value.returncode = 1
        run.return_value.stderr = "Audio server unavailable"
        with self.assertRaisesRegex(AudioError, "Audio server unavailable"):
            change_volume("up")


class MenuAndInstallTests(TestCase):
    def test_inject_restart_without_overwriting_custom_menu(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "menu.xml"
            old = (ROOT / "scripts/menu.xml").read_text()
            # Test an earlier Tres menu without the restart entry.
            old = old.replace(
                '    <item label="Restart Tres Panel">\n'
                '      <action name="Execute" command="~/.local/bin/tres-panel-control restart" />\n'
                '    </item>\n', '')
            path.write_text(old)
            self.assertTrue(add_restart_action(path, "/usr/bin/tres-panel-control restart"))
            self.assertFalse(add_restart_action(path, "/usr/bin/tres-panel-control restart"))
            ElementTree.parse(path)
            self.assertEqual(path.read_text().count('label="Restart Tres Panel"'), 1)
            self.assertIn('label="Exit"', path.read_text())

    def test_does_not_touch_unknown_menu(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "menu.xml"
            path.write_text('<openbox_menu><menu id="root-menu" /></openbox_menu>')
            self.assertFalse(add_restart_action(path, "/usr/bin/tres-panel-control restart"))
            self.assertNotIn("Restart Tres Panel", path.read_text())

    def test_manual_recovery_upgrade_keeps_autostart_user_lines(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            config = root / ".config/tres/labwc"
            config.mkdir(parents=True)
            original = (
                '#!/bin/sh\n'
                '"$HOME/.local/bin/tres-panel" >> "$HOME/.cache/tres/panel.log" 2>&1 &\n'
                '(sleep 1; wlr-randr --output eDP-1 --scale 1.5) &\n'
                'user-startup-command &\n'
            )
            (config / "autostart").write_text(original)
            (config / "menu.xml").write_text(
                (ROOT / "scripts/menu.xml").read_text()
            )
            script = ROOT / "scripts/install-panel-recovery.sh"
            for _ in range(2):
                proc = subprocess.run(
                    ["bash", str(script)],
                    env={**os.environ, "HOME": td},
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
            current = (config / "autostart").read_text()
            self.assertIn("tres-panel-supervisor", current)
            self.assertIn("--scale 1.5", current)
            self.assertIn("user-startup-command &", current)
            self.assertEqual(
                (config / "autostart.before-tres-supervisor").read_text(), original
            )
            self.assertTrue((root / ".local/bin/tres-panel-control").exists())


class PackageAndSessionTests(TestCase):
    def test_packaging_has_no_duplicate_entries_or_dependencies(self):
        files = (ROOT / "debian/tres.install").read_text().splitlines()
        self.assertEqual(len(files), len(set(files)))
        control = (ROOT / "debian/control").read_text()
        self.assertNotIn("wlr-randr, wlr-randr", control)

    def test_session_scripts_share_ownership_marker(self):
        installer = (ROOT / "install.sh").read_text()
        updater = (ROOT / "scripts/update-session.sh").read_text()
        session = (ROOT / "scripts/tres-session.sh").read_text()
        remover = (ROOT / "uninstall.sh").read_text()
        for content in (installer, updater, session, remover):
            self.assertIn("Tres-managed session launcher", content)
        self.assertIn("tres:labwc:wlroots", session)

    def test_tres_portals_are_desktop_scoped(self):
        config = (ROOT / "scripts/tres-portals.conf").read_text()
        self.assertIn("default=gtk", config)
        self.assertIn("org.freedesktop.impl.portal.ScreenCast=wlr", config)
        self.assertIn("org.freedesktop.impl.portal.FileChooser=gtk", config)
        self.assertIn("tres-portals.conf", (ROOT / "scripts/install-portals.sh").read_text())
        self.assertIn("dbus-update-activation-environment",
                      (ROOT / "scripts/autostart").read_text())


if __name__ == "__main__":
    import unittest
    unittest.main()
