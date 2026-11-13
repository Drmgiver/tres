"""Test the requested Wayland stacking behavior without a compositor."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "tres_panel.py"


class FakeLayerShell:
    class Layer:
        TOP = "top"
        BOTTOM = "bottom"

    def __init__(self):
        self.calls = []

    def set_layer(self, window, layer):
        self.calls.append(("layer", layer))

    def set_exclusive_zone(self, window, amount):
        self.calls.append(("exclusive", amount))

    def auto_exclusive_zone_enable(self, window):
        self.calls.append(("auto-exclusive",))


class TestPanelLayout(unittest.TestCase):
    def load_layout_method(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        cls = next(n for n in tree.body
                   if isinstance(n, ast.ClassDef) and n.name == "Tres")
        method = next(n for n in cls.body
                      if isinstance(n, ast.FunctionDef) and n.name == "_apply_mode")
        code = ast.Module(body=[ast.ClassDef(
            name="TestOnlyPanel", bases=[], keywords=[], body=[method],
            decorator_list=[])], type_ignores=[])
        fake = FakeLayerShell()
        namespace = {"GtkLayerShell": fake}
        exec(compile(ast.fix_missing_locations(code), str(SOURCE), "exec"), namespace)
        panel = namespace["TestOnlyPanel"]()
        panel.window = object()
        panel._layout_mode = None
        return panel, fake

    def test_under_allows_windows_to_cover_boxes(self):
        panel, shell = self.load_layout_method()
        panel._apply_mode("under")
        self.assertEqual(shell.calls, [("exclusive", 0), ("layer", "bottom")])
        self.assertEqual(panel._layout_mode, "under")

    def test_over_has_no_reserved_space(self):
        panel, shell = self.load_layout_method()
        panel._apply_mode("over")
        self.assertEqual(shell.calls, [("exclusive", 0), ("layer", "top")])
        self.assertEqual(panel._layout_mode, "over")

    def test_reserved_uses_independent_edge_surface(self):
        panel, shell = self.load_layout_method()
        panel._apply_mode("reserved")
        # The visible corner-anchored surface cannot safely claim an
        # exclusive zone. The separate edge-anchored reserver does that.
        self.assertEqual(shell.calls, [("exclusive", 0), ("layer", "top")])
        self.assertEqual(panel._layout_mode, "reserved")
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("def _reserve_work_area(", source)
        self.assertIn("GtkLayerShell.set_exclusive_zone(reserver, depth)", source)

    def test_reserved_can_be_undone_without_restart(self):
        panel, shell = self.load_layout_method()
        panel._apply_mode("reserved")
        shell.calls.clear()
        panel._apply_mode("under")
        self.assertEqual(shell.calls, [("exclusive", 0), ("layer", "bottom")])

    def test_invalid_mode_not_applied(self):
        panel, shell = self.load_layout_method()
        with self.assertRaises(ValueError):
            panel._apply_mode("unknown")
        self.assertEqual(shell.calls, [])


if __name__ == "__main__":
    unittest.main()
