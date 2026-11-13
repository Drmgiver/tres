"""Check the new Tres package/session branding and non-destructive migration."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestTresNaming(unittest.TestCase):
    def test_debian_name(self):
        control = (ROOT / "debian/control").read_text(encoding="utf-8")
        self.assertIn("Source: tres\n", control)
        self.assertIn("Package: tres\n", control)
        self.assertTrue((ROOT / "debian/tres.install").exists())
        self.assertTrue((ROOT / "debian/tres.docs").exists())
        self.assertFalse((ROOT / "debian/tres-labwc.install").exists())

    def test_session_is_named_tres(self):
        session = (ROOT / "packaging/deb/tres.desktop").read_text(encoding="utf-8")
        self.assertIn("\nName=Tres\n", session)
        self.assertIn("\nExec=/usr/bin/tres-session\n", session)
        self.assertTrue((ROOT / "packaging/deb/tres-session").exists())
        self.assertFalse((ROOT / "packaging/deb/tres-labwc.desktop").exists())

    def test_shell_installer_uses_new_name(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("Name=Tres\n", installer)
        self.assertIn("tres.desktop", installer)
        self.assertIn("~/.config", (ROOT / "README.md").read_text())
        self.assertIn("migrate-legacy.sh", installer)

    def test_migration_preserves_old_configuration_and_scale(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            old = home / ".config/tres-labwc/labwc"
            old.mkdir(parents=True)
            script = '#!/bin/sh\n# BEGIN TRES DISPLAY SCALE\n(sleep 1; wlr-randr --output eDP-1 --scale 1.5) &\n# END TRES DISPLAY SCALE\n'
            (old / "autostart").write_text(script, encoding="utf-8")
            (old.parent / "drm-device").write_text("/dev/dri/card1\n", encoding="utf-8")
            env = dict(os.environ, HOME=td)
            result = subprocess.run(["bash", str(ROOT / "scripts/migrate-legacy.sh")],
                                    capture_output=True, text=True, env=env, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            new = home / ".config/tres/labwc"
            self.assertEqual((new / "autostart").read_text(), script)
            self.assertEqual((old / "autostart").read_text(), script)
            self.assertEqual((new.parent / "drm-device").read_text(), "/dev/dri/card1\n")
            # Don't overwrite a user's newly customized Tres autostart.
            (new / "autostart").write_text("custom\n")
            result2 = subprocess.run(["bash", str(ROOT / "scripts/migrate-legacy.sh")],
                                     capture_output=True, text=True, env=env, check=False)
            self.assertEqual(result2.returncode, 0)
            self.assertEqual((new / "autostart").read_text(), "custom\n")


if __name__ == "__main__":
    unittest.main()
