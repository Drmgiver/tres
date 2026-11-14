"""Retiring experimental mouse bindings must not leave broken Labwc input."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class RestoreMouseTests(unittest.TestCase):
    def run_restore(self, home):
        return subprocess.run(
            ["bash", str(ROOT / "scripts/restore-panel-mouse.sh")],
            env={**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config")},
            capture_output=True, text=True, check=True,
        )

    def test_restores_expanded_default_bindings_and_keeps_custom(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            path = home / ".config/tres/labwc/rc.xml"
            path.parent.mkdir(parents=True)
            path.write_text(
                '<labwc_config><keyboard><default/></keyboard><mouse>'
                '<!-- BEGIN TRES DEFAULT MOUSE WITHOUT SUPER-LEFT -->'
                '<context name="Frame"><mousebind button="W-Right" action="Drag">'
                '<action name="Resize"/></mousebind></context>'
                '<!-- END TRES DEFAULT MOUSE WITHOUT SUPER-LEFT -->'
                '<context name="Root"><mousebind button="Right" action="Press">'
                '<action name="ShowMenu" menu="root-menu"/></mousebind></context>'
                '<!-- BEGIN TRES PANEL DRAG -->'
                '<context name="Frame"><mousebind button="A-Left" action="Drag">'
                '<action name="Move"/></mousebind></context>'
                '<!-- END TRES PANEL DRAG -->'
                '</mouse></labwc_config>'
            )
            self.run_restore(home)
            root = ET.parse(path).getroot()
            self.assertIsNotNone(root.find("./mouse/default"))
            self.assertIsNotNone(root.find("./keyboard/default"))
            self.assertIsNotNone(root.find("./mouse/context[@name='Root']"))
            self.assertNotIn("BEGIN TRES", path.read_text())
            before = path.read_text()
            self.run_restore(home)
            self.assertEqual(before, path.read_text())

    def test_removes_only_old_override_and_keeps_existing_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            path = home / ".config/tres/labwc/rc.xml"
            path.parent.mkdir(parents=True)
            path.write_text(
                '<labwc_config><mouse><default/>'
                '<!-- BEGIN TRES PANEL DRAG -->'
                '<context name="Frame"><mousebind button="W-Left" action="Drag"/></context>'
                '<!-- END TRES PANEL DRAG -->'
                '</mouse></labwc_config>')
            self.run_restore(home)
            self.assertEqual(path.read_text().count("<default/>"), 1)
            self.assertNotIn("W-Left", path.read_text())

    def test_unmanaged_config_is_untouched_and_trace_flag_cleaned(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            path = home / ".config/tres/labwc/rc.xml"
            path.parent.mkdir(parents=True)
            original = '<labwc_config><mouse><default/></mouse></labwc_config>'
            path.write_text(original)
            flag = home / ".config/tres/trace-panel-drag"
            flag.touch()
            self.run_restore(home)
            self.assertEqual(path.read_text(), original)
            self.assertFalse(flag.exists())
