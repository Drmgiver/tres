"""Long applications menus stay accessible on GTK3/Wayland without scroll arrows."""
import ast
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tres_core import submenu_pages  # noqa: E402


class TestMenuPagination(unittest.TestCase):
    def test_small_categories_have_one_unchanged_section(self):
        for count in range(1, 13):
            self.assertEqual(submenu_pages(count), [(0, count)])
        self.assertEqual(submenu_pages(0), [])

    def test_large_categories_have_no_missing_or_repeated_items(self):
        for count in (13, 24, 25, 48, 145, 200, 1000, 2500):
            pages = submenu_pages(count)
            self.assertLessEqual(len(pages), 12)
            self.assertEqual([item for start, end in pages for item in range(start, end)],
                             list(range(count)))
            self.assertTrue(all(start < end for start, end in pages))

    def test_rejects_invalid_sizes(self):
        with self.assertRaises(ValueError):
            submenu_pages(-1)
        with self.assertRaises(ValueError):
            submenu_pages(5, max_rows=1)

    def test_panel_reaches_last_application_and_binds_correct_launcher(self):
        # Exercise the real panel method without importing GTK or opening a window.
        source = ROOT / "src" / "tres_panel.py"
        parsed = ast.parse(source.read_text(encoding="utf-8"))
        tres = next(node for node in parsed.body
                    if isinstance(node, ast.ClassDef) and node.name == "Tres")
        rows = next(node for node in tres.body
                    if isinstance(node, ast.FunctionDef) and
                    node.name == "_application_rows")
        isolated = ast.Module(body=[ast.ClassDef(
            name="PanelUnderTest", bases=[], keywords=[], body=[rows],
            decorator_list=[])], type_ignores=[])
        namespace = {"submenu_pages": submenu_pages}
        exec(compile(ast.fix_missing_locations(isolated), str(source), "exec"), namespace)

        class FakeApp:
            def __init__(self, name):
                self.name = name

            def get_name(self):
                return self.name

        class Panel(namespace["PanelUnderTest"]):
            @staticmethod
            def item(name, callback):
                return ("app", name, callback)

            @staticmethod
            def submenu(label, children):
                return ("page", label, children)

            @staticmethod
            def launch_app(app):
                return app.name

        panel = Panel()
        apps = [FakeApp(f"Multimedia App {i:03}") for i in range(200)]
        tree = panel._application_rows(apps)

        def visit(rows):
            self.assertLessEqual(len(rows), 12)
            for row in rows:
                if row[0] == "app":
                    yield (row[1], row[2]())
                else:
                    yield from visit(row[2])

        actual = list(visit(tree))
        expected = [(app.name, app.name) for app in apps]
        self.assertEqual(actual, expected)
        self.assertEqual(actual[-1][0], "Multimedia App 199")


if __name__ == "__main__":
    unittest.main()
