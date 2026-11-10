import unittest
from unittest.mock import patch
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from tres_core import Toplevel, parse_toplevels, activate  # noqa: E402


class TestCore(unittest.TestCase):
    def test_parse_empty(self):
        self.assertEqual(parse_toplevels("\n"), [])

    def test_multiple_and_colon_title(self):
        self.assertEqual(parse_toplevels("firefox: Site: Page\nfoot: Terminal\n"), [
            Toplevel("firefox", "Site: Page"), Toplevel("foot", "Terminal")])

    def test_ignore_unknown_lines(self):
        self.assertEqual(parse_toplevels("garbage\n : Empty\n"), [])

    @patch("tres_core.subprocess.run")
    def test_activation_without_shell(self, run):
        run.return_value.returncode = 0
        activate(Toplevel("firefox", "A: title"))
        self.assertEqual(run.call_args.args[0], ["wlrctl", "window", "focus",
                                                  "app_id:firefox", "title:A: title"])

if __name__ == '__main__':
    unittest.main()
