"""Regression tests for Tres-scoped Polkit startup."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PolkitTests(unittest.TestCase):
    def test_shell_syntax(self):
        for name in ("scripts/tres-polkit-agent.sh", "scripts/install-polkit.sh"):
            subprocess.run(["bash", "-n", str(ROOT / name)], check=True)

    def test_installer_idempotent_and_preserves_custom_autostart(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            startup = home / ".config/tres/labwc/autostart"
            startup.parent.mkdir(parents=True)
            startup.write_text("# custom startup\nprintf 'existing behavior' >/dev/null\n")
            env = dict(os.environ, HOME=str(home))
            installer = str(ROOT / "scripts/install-polkit.sh")
            for _ in range(2):
                subprocess.run(["bash", installer], env=env, check=True, capture_output=True, text=True)
            content = startup.read_text()
            self.assertIn("# custom startup", content)
            self.assertEqual(content.count('"$HOME/.local/bin/tres-polkit-agent"'), 1)
            self.assertTrue((home / ".local/bin/tres-polkit-agent").exists())

    def test_other_desktop_skips_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, XDG_CURRENT_DESKTOP="GNOME", PATH="/usr/bin:/bin")
            result = subprocess.run(["sh", str(ROOT / "scripts/tres-polkit-agent.sh")],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")

    def test_source_and_package_autostart(self):
        source = (ROOT / "scripts/autostart").read_text()
        package = (ROOT / "packaging/deb/autostart").read_text()
        self.assertIn("tres-polkit-agent", source)
        self.assertIn("tres-polkit-agent.sh", package)
        self.assertIn("lxpolkit", (ROOT / "debian/control").read_text())


if __name__ == "__main__":
    unittest.main()
