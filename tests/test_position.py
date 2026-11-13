"""Placement regression tests: all edges, precise center, and persistence."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tres_position import (DEFAULT_POSITION, EDGES, panel_size, origin,
                           coordinates, with_coordinates, read_position,
                           save_position, validate_position)


class PositionTests(unittest.TestCase):
    def test_middle_square_is_exact_center_reference(self):
        width, height = panel_size(19)
        # Center group: 3 equal squares and equal spacing makes square #2 central.
        x, y = coordinates(DEFAULT_POSITION, width, height, 1920, 1080)
        self.assertEqual((width, height), (67, 19))
        self.assertEqual(y, 3)
        self.assertEqual(x + 19 + 5 + 19 / 2, 960.5)
        self.assertLess(abs(x + 19 + 5 + 19 / 2 - 960), 1)

    def test_edge_presets(self):
        width, height = panel_size(19)
        for edge in EDGES:
            with self.subTest(edge=edge):
                x, y = coordinates({"edge": edge, "x": 0, "y": 0},
                                   width, height, 1920, 1080)
                if edge == "top":
                    self.assertEqual(y, 3)
                elif edge == "bottom":
                    self.assertEqual(y, 1058)
                elif edge == "left":
                    self.assertEqual(x, 3)
                else:
                    self.assertEqual(x, 1850)

    def test_offsets_can_move_in_both_axes(self):
        width, height = panel_size(19)
        desired = (450, 230)
        for edge in EDGES:
            position = with_coordinates(edge, *desired, width, height, 1920, 1080)
            self.assertEqual(coordinates(position, width, height, 1920, 1080),
                             desired)

    def test_clamp_squares_on_screen(self):
        width, height = panel_size(19)
        self.assertEqual(coordinates({"edge": "top", "x": -20000, "y": 20000},
                                     width, height, 1920, 1080), (0, 1061))

    def test_persistence_and_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "panel-position.json"
            self.assertEqual(read_position(path), DEFAULT_POSITION)
            state = {"edge": "right", "x": -80, "y": 37}
            save_position(state, path)
            self.assertEqual(read_position(path), state)
            for bad in ({"edge": "middle", "x": 0, "y": 0},
                        {"edge": "top", "x": "0", "y": 0},
                        {"edge": "top", "x": 0, "y": 0, "extra": 1}):
                with self.assertRaises(ValueError):
                    save_position(bad, path)
                self.assertEqual(read_position(path), state)

    def test_panel_integrated_in_settings_and_installers(self):
        panel = (ROOT / "src/tres_panel.py").read_text()
        settings = (ROOT / "src/tres_config.py").read_text()
        self.assertIn("Gdk.ModifierType.SUPER_MASK", panel)
        self.assertIn("save_position(self._position)", panel)
        self.assertIn('label("Side:")', settings)
        self.assertIn("save_position({", settings)
        self.assertIn("tres_position.py", (ROOT / "scripts/update-panel.sh").read_text())
        self.assertIn("tres_position.py", (ROOT / "debian/tres.install").read_text())


if __name__ == "__main__":
    unittest.main()
