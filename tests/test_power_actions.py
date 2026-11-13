"""Safe power actions: no real restart or shutdown commands are run in tests."""
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from tres_core import request_power_action  # noqa: E402


class TestPowerActions(unittest.TestCase):
    @patch("tres_core.subprocess.run")
    def test_restart_requests_systemctl_reboot(self, run):
        run.return_value.returncode = 0
        request_power_action("restart")
        run.assert_called_once_with(
            ["systemctl", "reboot"], capture_output=True, text=True,
            timeout=15.0, check=False,
        )

    @patch("tres_core.subprocess.run")
    def test_shutdown_requests_systemctl_poweroff(self, run):
        run.return_value.returncode = 0
        request_power_action("shutdown")
        run.assert_called_once_with(
            ["systemctl", "poweroff"], capture_output=True, text=True,
            timeout=15.0, check=False,
        )

    @patch("tres_core.subprocess.run")
    def test_unknown_action_never_invokes_systemctl(self, run):
        with self.assertRaises(ValueError):
            request_power_action("suspend")
        run.assert_not_called()

    @patch("tres_core.subprocess.run")
    def test_denied_request_reports_reason(self, run):
        run.return_value.returncode = 1
        run.return_value.stderr = "Access denied"
        with self.assertRaisesRegex(RuntimeError, "Access denied"):
            request_power_action("shutdown")

    @patch("tres_core.subprocess.run", side_effect=FileNotFoundError("systemctl missing"))
    def test_missing_command_reports_failure(self, run):
        with self.assertRaisesRegex(RuntimeError, "systemctl missing"):
            request_power_action("restart")


if __name__ == "__main__":
    unittest.main()
