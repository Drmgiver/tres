"""Verify Grim/Slurp are invoked safely and the Accessories launcher exists."""
import os
import pathlib
import subprocess
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
from subprocess import CompletedProcess, TimeoutExpired

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tres_capture import CaptureCancelled, CaptureError, capture  # noqa: E402


class CaptureTests(unittest.TestCase):
    @patch("tres_capture.shutil.which", return_value="/usr/bin/grim")
    @patch("tres_capture.subprocess.run")
    def test_full_screen_uses_grim_without_shell(self, run, _which):
        run.return_value = CompletedProcess(["grim"], 0, "", "")
        result = capture("/tmp/test.png")
        self.assertEqual(result, pathlib.Path("/tmp/test.png"))
        run.assert_called_once_with(
            ["grim", "/tmp/test.png"], capture_output=True, text=True, timeout=45,
            check=False,
        )

    @patch("tres_capture.shutil.which", return_value="/usr/bin/tool")
    @patch("tres_capture.subprocess.run")
    def test_region_capture_uses_slurp_geometry(self, run, _which):
        run.side_effect = [
            CompletedProcess(["slurp"], 0, "100,200 400x300\n", ""),
            CompletedProcess(["grim"], 0, "", ""),
        ]
        capture("/tmp/crop.png", select_region=True)
        self.assertEqual(run.call_args_list[0].args[0], ["slurp"])
        self.assertEqual(run.call_args_list[1].args[0],
                         ["grim", "-g", "100,200 400x300", "/tmp/crop.png"])

    @patch("tres_capture.shutil.which", return_value="/usr/bin/tool")
    @patch("tres_capture.subprocess.run")
    def test_cancelled_selection_never_runs_grim(self, run, _which):
        run.return_value = CompletedProcess(["slurp"], 1, "", "")
        with self.assertRaises(CaptureCancelled):
            capture("/tmp/crop.png", select_region=True)
        run.assert_called_once()

    @patch("tres_capture.shutil.which", return_value="/usr/bin/tool")
    @patch("tres_capture.subprocess.run")
    def test_grim_errors_are_reported(self, run, _which):
        run.return_value = CompletedProcess(["grim"], 1, "", "Unable to grab output")
        with self.assertRaisesRegex(CaptureError, "Unable to grab output"):
            capture("/tmp/nope.png")

    @patch("tres_capture.shutil.which", return_value=None)
    def test_missing_grim_is_clear(self, _which):
        with self.assertRaisesRegex(CaptureError, "Grim is not installed"):
            capture("/tmp/nope.png")

    @patch("tres_capture.shutil.which", side_effect=lambda x: "/usr/bin/grim" if x == "grim" else None)
    def test_missing_slurp_is_clear(self, _which):
        with self.assertRaisesRegex(CaptureError, "Slurp is not installed"):
            capture("/tmp/nope.png", select_region=True)

    def test_install_message_mentions_only_tres(self):
        with TemporaryDirectory() as temp_home:
            env = {**os.environ, "HOME": temp_home}
            command = ["bash", str(ROOT / "scripts/install-screenshot.sh")]
            result = subprocess.run(
                command, env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.strip(),
                "Tres Screenshot added to Accessories.",
            )
            self.assertTrue(
                (pathlib.Path(temp_home) / ".local/bin/tres-screenshot").is_file()
            )
            self.assertTrue(
                (pathlib.Path(temp_home) /
                 ".local/share/applications/tres-screenshot.desktop").is_file()
            )

    def test_desktop_launcher_is_accessories(self):
        for name in ("scripts/tres-screenshot.desktop", "packaging/deb/tres-screenshot.desktop"):
            data = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("Name=Tres Screenshot", data)
            self.assertIn("Categories=Utility;GTK;", data)
            self.assertIn("Terminal=false", data)


if __name__ == "__main__":
    unittest.main()
