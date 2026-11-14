"""Tres-only Labwc input binding conflict regression tests."""
import sys
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tres_mouse import configure


class MouseBindingTests(unittest.TestCase):
    def test_default_config_frees_super_and_moves_window_drag_to_alt(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = Path(tmp) / "rc.xml"
            rc.write_text("<labwc_config><keyboard><default /></keyboard></labwc_config>")
            self.assertEqual(configure(rc), "installed")
            self.assertEqual(configure(rc), "already-installed")
            root = ET.parse(rc).getroot()
            contexts = root.findall("./mouse/context")
            frame = next(x for x in contexts if x.get("name") == "Frame")
            binds = {(b.get("button"), b.get("action")): b
                     for b in frame.findall("mousebind")}
            self.assertNotIn(("W-Left", "Drag"), binds)
            self.assertNotIn(("W-Left", "Press"), binds)
            self.assertIsNone(root.find("./mouse/default"))
            self.assertIsNotNone(root.find("./keyboard/default"))
            self.assertIsNotNone(root.find("./mouse/context[@name='Root']"))
            self.assertEqual(binds[("A-Left", "Drag")].find("action").get("name"), "Move")
            self.assertEqual(rc.read_text().count("BEGIN TRES PANEL DRAG"), 1)

    def test_preserves_unrelated_mouse_bindings_and_keyboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = Path(tmp) / "rc.xml"
            rc.write_text(
                '<labwc_config><keyboard><keybind key="W-space"/></keyboard>'
                '<mouse><default/><context name="Root">'
                '<mousebind button="Right" action="Press">'
                '<action name="ShowMenu"/></mousebind></context></mouse>'
                '</labwc_config>')
            self.assertEqual(configure(rc), "installed")
            xml = ET.parse(rc).getroot()
            self.assertIsNotNone(xml.find("./keyboard/keybind"))
            self.assertIsNotNone(xml.find("./mouse/context[@name='Root']"))

    def test_refuses_to_replace_custom_super_or_alt_binding(self):
        for key in ("W-Left", "A-Left"):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                rc = Path(tmp) / "rc.xml"
                data = ('<labwc_config><mouse><context name="Frame">'
                        f'<mousebind button="{key}" action="Drag">'
                        '<action name="Custom"/></mousebind>'
                        '</context></mouse></labwc_config>')
                rc.write_text(data)
                self.assertEqual(configure(rc), "skip-custom-mouse-config")
                self.assertEqual(rc.read_text(), data)

    def test_upgrade_migrates_old_empty_frame_bindings(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = Path(tmp) / "rc.xml"
            rc.write_text(
                '<labwc_config><mouse><default/>'
                '<!-- BEGIN TRES PANEL DRAG -->'
                '<context name="Frame">'
                '<mousebind button="W-Left" action="Press" />'
                '<mousebind button="W-Left" action="Drag" />'
                '<mousebind button="A-Left" action="Drag"><action name="Move" /></mousebind>'
                '</context>'
                '<!-- END TRES PANEL DRAG -->'
                '</mouse></labwc_config>'
            )
            self.assertEqual(configure(rc), "upgraded")
            xml = ET.parse(rc).getroot()
            self.assertIsNone(xml.find("./mouse/default"))
            self.assertEqual(configure(rc), "already-installed")
            frame_binds = [
                node for context in xml.findall("./mouse/context")
                if context.get("name") == "Frame"
                for node in context.findall("mousebind")
            ]
            self.assertTrue(any(node.get("button") == "A-Left" for node in frame_binds))
            self.assertFalse(any(node.get("button") == "W-Left" for node in frame_binds))
            self.assertEqual(rc.read_text().count("BEGIN TRES PANEL DRAG"), 1)

    def test_safeguards_custom_symlink_and_invalid_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "original.xml"
            original.write_text("<invalid")
            link = Path(tmp) / "rc.xml"
            link.symlink_to(original)
            self.assertEqual(configure(link), "skip-symlink")
            with self.assertRaises(ET.ParseError):
                configure(original)
            self.assertEqual(original.read_text(), "<invalid")

    def test_upgrade_uses_private_config_only(self):
        update = (ROOT / "scripts/update-panel.sh").read_text()
        self.assertIn("install-panel-drag.sh", update)
        self.assertIn("tres_mouse.py", update)
        installer = (ROOT / "install.sh").read_text()
        self.assertIn("install-panel-drag.sh", installer)
