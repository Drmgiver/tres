#!/usr/bin/python3
"""Launch the terminal chosen in Tres Settings."""
from __future__ import annotations

import shutil
import subprocess
import sys

from tres_preferences import TERMINALS, read_terminal


def open_terminal() -> None:
    selected = read_terminal()
    choices = ([selected] if selected != "auto" else []) + list(TERMINALS)
    seen = set()
    for binary in choices:
        if binary in seen:
            continue
        seen.add(binary)
        if shutil.which(binary):
            try:
                subprocess.Popen([binary], start_new_session=True,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return
            except OSError:
                continue
    raise RuntimeError("No compatible terminal is installed. Try sudo apt install foot.")


def main():
    try:
        open_terminal()
    except RuntimeError as error:
        print(f"Tres Terminal: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
