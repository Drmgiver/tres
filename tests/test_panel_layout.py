"""Regression tests for the three-square panel's maximized-window behavior.

Source inspection avoids depending on a Wayland session in GitHub Actions.
The end-to-end test remains opening a maximized window in standalone Labwc.
"""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "tres_panel.py"


def named_call(stmt):
    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        return None
    func = stmt.value.func
    parts = []
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if isinstance(func, ast.Name):
        parts.append(func.id)
        return ".".join(reversed(parts))
    return None


class TestPanelLayout(unittest.TestCase):
    def test_maximized_windows_respect_panel(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        cls = next(n for n in tree.body
                   if isinstance(n, ast.ClassDef) and n.name == "Tres")
        init = next(n for n in cls.body
                    if isinstance(n, ast.FunctionDef) and n.name == "__init__")
        calls = [named_call(stmt) for stmt in init.body]
        margin = calls.index("GtkLayerShell.set_margin")
        reserve = calls.index("GtkLayerShell.auto_exclusive_zone_enable")
        show = calls.index("self.window.show_all")
        self.assertLess(margin, reserve)
        self.assertLess(reserve, show)
        self.assertNotIn("GtkLayerShell.set_exclusive_zone", calls,
                         "An explicit zone may disable automatic reservation")


if __name__ == "__main__":
    unittest.main()
