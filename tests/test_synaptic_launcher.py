"""Regression checks for the isolated Synaptic XWayland compatibility launcher."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/tres-synaptic.sh"


class SynapticTests(unittest.TestCase):
    def test_syntax(self):
        subprocess.run(["bash", "-n", str(LAUNCHER)], check=True)

    def test_menu_special_cases_only_synaptic(self):
        # App launch policy is shared by the menu and application search.
        shared = (ROOT / "src/tres_applications.py").read_text()
        panel = (ROOT / "src/tres_panel.py").read_text()
        self.assertIn('("synaptic.desktop", "synaptic-pkexec.desktop")', shared)
        self.assertIn('app.launch([], None)', shared)
        self.assertIn('tres-synaptic', shared)
        self.assertIn('from tres_applications import visible_applications, launch_application', panel)
        self.assertIn('return launch_application(app)', panel)

    def test_grant_and_revoke_even_when_synaptic_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            binpath = directory / "bin"
            binpath.mkdir()
            events = directory / "events"
            for name, body in {
                "xhost": '#!/bin/sh\nif [ "$#" -eq 0 ]; then exit 0; fi\nprintf "%s\\n" "$1" >> "$TRES_TEST_EVENTS"\n',
                "synaptic-pkexec": '#!/bin/sh\nprintf "synaptic-called\\n" >> "$TRES_TEST_EVENTS"\nexit 7\n',
            }.items():
                path = binpath / name
                path.write_text(body)
                path.chmod(0o755)
            env = dict(os.environ, HOME=tmp, XDG_RUNTIME_DIR=tmp,
                       DISPLAY=":99", PATH=f"{binpath}:/usr/bin:/bin",
                       TRES_TEST_EVENTS=str(events))
            result = subprocess.run(["bash", str(LAUNCHER)], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertEqual(events.read_text().splitlines(), [
                "+si:localuser:root", "synaptic-called", "-si:localuser:root"
            ])

    def test_no_display_never_grants_access(self):
        env = dict(os.environ)
        env.pop("DISPLAY", None)
        result = subprocess.run(["bash", str(LAUNCHER)], env=env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DISPLAY", result.stderr)


if __name__ == "__main__":
    unittest.main()
