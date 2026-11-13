"""Volume label parsing regressions for PipeWire and PulseAudio."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tres_audio import volume_label


class VolumeLabelTests(TestCase):
    @patch("tres_audio.subprocess.run")
    @patch("tres_audio.audio_backend", return_value="wpctl")
    def test_wpctl_normal_volume(self, _backend, run):
        run.return_value = SimpleNamespace(returncode=0, stdout="Volume: 0.65\n", stderr="")
        self.assertEqual(volume_label(), "Volume: 65%")

    @patch("tres_audio.subprocess.run")
    @patch("tres_audio.audio_backend", return_value="wpctl")
    def test_wpctl_muted(self, _backend, run):
        run.return_value = SimpleNamespace(returncode=0, stdout="Volume: 0.42 [MUTED]\n", stderr="")
        self.assertEqual(volume_label(), "Volume: 42% (muted)")

    @patch("tres_audio.subprocess.run")
    @patch("tres_audio.audio_backend", return_value="pactl")
    def test_pactl_muted(self, _backend, run):
        run.side_effect = [
            SimpleNamespace(returncode=0, stdout="Volume: front-left: 32768 /  50% / -18.06 dB\n", stderr=""),
            SimpleNamespace(returncode=0, stdout="Mute: yes\n", stderr=""),
        ]
        self.assertEqual(volume_label(), "Volume: 50% (muted)")

    @patch("tres_audio.subprocess.run")
    @patch("tres_audio.audio_backend", return_value="wpctl")
    def test_unavailable_only_on_failure(self, _backend, run):
        run.return_value = SimpleNamespace(returncode=1, stdout="", stderr="failed")
        self.assertEqual(volume_label(), "Volume: unavailable")
