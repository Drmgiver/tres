"""Search hotkey and audio readout regression tests."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import tres_audio
from tres_shortcuts import read_shortcuts, DEFAULT_KEYS


class AudioReadoutTests(unittest.TestCase):
    @patch("tres_audio.audio_backend", return_value="wpctl")
    @patch("tres_audio.subprocess.run")
    def test_wpctl_volume_and_mute(self, run, _backend):
        run.return_value = Mock(returncode=0, stdout="Volume: 0.43", stderr="")
        self.assertEqual(tres_audio.volume_label(), "Volume: 43%")
        run.return_value = Mock(returncode=0, stdout="Volume: 0.43 [MUTED]", stderr="")
        self.assertEqual(tres_audio.volume_label(), "Volume: 43% (muted)")

    @patch("tres_audio.audio_backend", return_value="pactl")
    @patch("tres_audio.subprocess.run")
    def test_pactl_volume_and_mute(self, run, _backend):
        run.side_effect = [
            Mock(returncode=0, stdout="Volume: front-left: 32768 / 50% / -18 dB", stderr=""),
            Mock(returncode=0, stdout="Mute: yes", stderr=""),
        ]
        self.assertEqual(tres_audio.volume_label(), "Volume: 50% (muted)")

    @patch("tres_audio.audio_backend", return_value="wpctl")
    @patch("tres_audio.subprocess.run")
    def test_missing_sink_is_unavailable(self, run, _backend):
        run.return_value = Mock(returncode=1, stdout="", stderr="no sink")
        self.assertEqual(tres_audio.volume_label(), "Volume: unavailable")


class SearchShortcutTests(unittest.TestCase):
    def test_suggested_shortcut(self):
        self.assertEqual(DEFAULT_KEYS["search"], "W-space")

    def test_initialize_without_overwriting_existing_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            rc = home / ".config/tres/labwc/rc.xml"
            rc.parent.mkdir(parents=True)
            rc.write_text('<labwc_config><keyboard><default />'
                          '<keybind key="W-f"><action name="Execute" command="my-file-manager" /></keybind>'
                          '</keyboard></labwc_config>')
            env = dict(os.environ, HOME=temp)
            script = str(ROOT / "scripts/install-search-shortcut.sh")
            for _ in range(2):
                proc = subprocess.run(["bash", script], env=env,
                                      capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
            content = rc.read_text()
            self.assertIn('key="W-f"', content)
            self.assertEqual(content.count('key="W-space"'), 1)
            self.assertEqual(read_shortcuts(rc)["search"], "W-space")

    def test_existing_super_space_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            rc = home / ".config/tres/labwc/rc.xml"
            rc.parent.mkdir(parents=True)
            original = ('<labwc_config><keyboard><keybind key="W-space">'
                        '<action name="Execute" command="existing-launcher" />'
                        '</keybind></keyboard></labwc_config>')
            rc.write_text(original)
            result = subprocess.run(["bash", str(ROOT / "scripts/install-search-shortcut.sh")],
                                    env=dict(os.environ, HOME=temp), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(rc.read_text(), original)


if __name__ == "__main__":
    unittest.main()
