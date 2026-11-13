"""Check Tres's requested Wayland stacking behavior without a compositor."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "tres_panel.py"


class TestPanelLayout(unittest.TestCase):
    def test_normal_and_maximized_windows_cover_three_squares(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        cls = next(n for n in tree.body
                   if isinstance(n, ast.ClassDef) and n.name == "Tres")
        init = next(n for n in cls.body
                    if isinstance(n, ast.FunctionDef) and n.name == "__init__")
        calls = [
            node.value for node in init.body
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        ]
        def find(name):
            return [
                call for call in calls
                if isinstance(call.func, ast.Attribute)
                and call.func.attr == name
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "GtkLayerShell"
            ]

        layers = find("set_layer")
        self.assertEqual(len(layers), 1)
        self.assertEqual(ast.unparse(layers[0].args[1]),
                         "GtkLayerShell.Layer.BOTTOM")
        zones = find("set_exclusive_zone")
        self.assertEqual(len(zones), 1)
        self.assertEqual(ast.literal_eval(zones[0].args[1]), 0)
        self.assertFalse(find("auto_exclusive_zone_enable"))


if __name__ == "__main__":
    unittest.main()
