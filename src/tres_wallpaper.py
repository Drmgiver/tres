#!/usr/bin/python3
"""Start Tres's own swaybg wallpaper with the configured solid color."""
import shutil
import subprocess
import sys
from tres_preferences import read_appearance


def main():
    if not shutil.which("swaybg"):
        sys.exit("Tres wallpaper: swaybg is not installed.")
    color = read_appearance()["wallpaper_color"]
    # This process becomes the wallpaper helper; it does not alter COSMIC.
    raise SystemExit(subprocess.call(["swaybg", "-c", color]))


if __name__ == "__main__":
    main()
