"""Super+drag capture-phase input regression checks."""
import ast
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/tres_panel.py"
sys.path.insert(0, str(ROOT / "src"))
from tres_position import coordinates, with_coordinates


class DragTests(unittest.TestCase):
    def make_panel(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "Tres")
        names = {"_super_pressed", "_gesture_begin", "_gesture_update",
                 "_gesture_end", "_gesture_cancel"}
        methods = [node for node in cls.body if isinstance(node, ast.FunctionDef)
                   and node.name in names]
        module = ast.Module(body=[ast.ClassDef(
            name="PanelOnly", bases=[], keywords=[], body=methods,
            decorator_list=[])], type_ignores=[])
        namespace = {
            "Gdk": SimpleNamespace(ModifierType=SimpleNamespace(
                MOD4_MASK=64, SUPER_MASK=1 << 26)),
            "Gtk": SimpleNamespace(EventSequenceState=SimpleNamespace(
                DENIED="denied", CLAIMED="claimed")),
            "coordinates": coordinates, "with_coordinates": with_coordinates,
            "save_position": lambda _state: None,
        }
        exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"),
             namespace)
        panel = namespace["PanelOnly"]()
        panel._position = {"edge": "top", "x": 0, "y": 0}
        panel._drag = None
        panel._suppress_click = False
        panel._monitor_dimensions = lambda: (1920, 1080)
        panel._panel_dimensions = lambda: (67, 19)
        moved = []
        panel._apply_position = lambda position: moved.append(position.copy())
        return panel, moved

    @staticmethod
    def gesture(state):
        class FakeGesture:
            def __init__(self):
                self.claim = None
            def get_last_event(self, sequence):
                return SimpleNamespace(state=state)
            def set_state(self, state):
                self.claim = state
        return FakeGesture()

    def test_unmodified_click_is_not_claimed(self):
        panel, moved = self.make_panel()
        gesture = self.gesture(0)
        panel._gesture_begin(gesture, 4, 4)
        self.assertEqual(gesture.claim, "denied")
        self.assertIsNone(panel._drag)

    def test_mod4_drag_claimed_and_saved(self):
        panel, positions = self.make_panel()
        gesture = self.gesture(64)
        panel._gesture_begin(gesture, 4, 4)
        self.assertEqual(gesture.claim, "claimed")
        panel._gesture_update(gesture, 11, 9)
        self.assertEqual((panel._position["x"], panel._position["y"]), (11, 9))
        panel._gesture_end(gesture, 11, 9)
        self.assertIsNone(panel._drag)
        self.assertTrue(panel._suppress_click)
        self.assertTrue(positions)

    def test_updates_use_incremental_offset(self):
        panel, _ = self.make_panel()
        gesture = self.gesture(1 << 26)
        panel._gesture_begin(gesture, 4, 4)
        panel._gesture_update(gesture, 10, 0)
        panel._gesture_update(gesture, 18, 0)
        self.assertEqual(panel._position["x"], 18)

    def test_uses_capture_phase_before_square_button(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("Gtk.GestureDrag.new(self.window)", source)
        self.assertIn("Gtk.PropagationPhase.CAPTURE", source)
        self.assertNotIn('btn.connect("button-press-event", self._drag_press)', source)
