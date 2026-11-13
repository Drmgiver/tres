"""Exercise Tres's Wayland-safe Super+drag event path without GTK."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "tres_panel.py"


class DragTests(unittest.TestCase):
    @staticmethod
    def mock_panel():
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        cls = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef) and node.name == "Tres")
        names = {"_super_pressed", "_drag_press", "_drag_motion", "_drag_release"}
        methods = [node for node in cls.body
                   if isinstance(node, ast.FunctionDef) and node.name in names]
        module = ast.Module(
            body=[ast.ClassDef(name="PanelOnly", bases=[], keywords=[],
                               body=methods, decorator_list=[])],
            type_ignores=[])
        from sys import path
        path.insert(0, str(ROOT / "src"))
        from tres_position import coordinates, with_coordinates
        modifiers = SimpleNamespace(MOD4_MASK=64, SUPER_MASK=1 << 26)
        ns = {"Gdk": SimpleNamespace(ModifierType=modifiers),
              "coordinates": coordinates, "with_coordinates": with_coordinates,
              "save_position": lambda _p: None, "sys": SimpleNamespace(stderr=None)}
        exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), ns)
        panel = ns["PanelOnly"]()
        panel._position = {"edge": "top", "x": 0, "y": 0}
        panel._drag = None
        panel._suppress_click = False
        panel._monitor_dimensions = lambda: (1920, 1080)
        panel._panel_dimensions = lambda: (67, 19)
        recorded = []
        panel._apply_position = lambda position: recorded.append(position.copy())
        return panel, recorded

    def test_logo_key_mod4_starts_drag_without_root_coordinates(self):
        panel, recorded = self.mock_panel()
        self.assertFalse(panel._drag_press(None, SimpleNamespace(
            button=1, state=0, x=8.0, y=8.0)))
        self.assertTrue(panel._drag_press(None, SimpleNamespace(
            button=1, state=64, x=8.0, y=8.0)))
        self.assertEqual(panel._drag, (8.0, 8.0, False))
        self.assertTrue(panel._drag_motion(None, SimpleNamespace(x=17.0, y=8.0)))
        self.assertEqual(panel._position["x"], 9)
        self.assertTrue(recorded)
        self.assertTrue(panel._drag_release(None, SimpleNamespace(button=1)))
        self.assertIsNone(panel._drag)

    def test_drag_delta_tracks_moving_widget_not_global_position(self):
        panel, recorded = self.mock_panel()
        panel._drag_press(None, SimpleNamespace(button=1, state=64, x=5, y=5))
        panel._drag_motion(None, SimpleNamespace(x=15, y=5))
        self.assertEqual(panel._position["x"], 10)
        # After moving the surface, pointer is near the originally pressed
        # local point; another 8px motion must add rather than restart.
        panel._drag_motion(None, SimpleNamespace(x=13, y=5))
        self.assertEqual(panel._position["x"], 18)
        self.assertEqual(len(recorded), 2)

    def test_super_mask_also_supported(self):
        panel, _ = self.mock_panel()
        self.assertTrue(panel._drag_press(None, SimpleNamespace(
            button=1, state=1 << 26, x=1, y=2)))
