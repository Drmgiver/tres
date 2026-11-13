"""Audio controls for Tres via the available PipeWire/PulseAudio client."""
from __future__ import annotations

import shutil
import subprocess


class AudioError(RuntimeError):
    pass


def audio_backend() -> str | None:
    # WirePlumber systems commonly provide wpctl, while other installs
    # expose pactl. Both control the existing audio server, not a new daemon.
    for binary in ("wpctl", "pactl"):
        if shutil.which(binary):
            return binary
    return None


def change_volume(direction: str) -> None:
    if direction not in ("up", "down", "mute"):
        raise ValueError("Invalid audio command.")
    backend = audio_backend()
    if backend is None:
        raise AudioError("Install WirePlumber (wpctl) or pulseaudio-utils (pactl).")
    if backend == "wpctl":
        args = ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"] if direction == "mute" else [
            "wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+" if direction == "up" else "5%-",
        ]
    else:
        args = [
            "pactl", "set-sink-mute" if direction == "mute" else "set-sink-volume",
            "@DEFAULT_SINK@", "toggle" if direction == "mute" else "+5%" if direction == "up" else "-5%",
        ]
    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AudioError(f"Audio control failed: {error}") from error
    if proc.returncode:
        raise AudioError(
            (proc.stderr or proc.stdout or "The audio server rejected the command.").strip()
        )

def volume_label() -> str:
    """Read the current default output level without changing it."""
    import re

    backend = audio_backend()
    if backend is None:
        return "Volume: unavailable"
    command = (["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]
               if backend == "wpctl" else
               ["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=3, check=False)
        if proc.returncode:
            return "Volume: unavailable"
        if backend == "wpctl":
            match = re.search(r"Volume:\\s*([0-9]+(?:\\.[0-9]+)?)", proc.stdout)
            if not match:
                return "Volume: unavailable"
            level = round(float(match.group(1)) * 100)
            muted = "[MUTED]" in proc.stdout
        else:
            match = re.search(r"([0-9]+)%", proc.stdout)
            if not match:
                return "Volume: unavailable"
            level = int(match.group(1))
            mute = subprocess.run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"],
                                  capture_output=True, text=True, timeout=3,
                                  check=False)
            muted = mute.returncode == 0 and bool(re.search(
                r"Mute:\\s*yes", mute.stdout, re.IGNORECASE))
        return f"Volume: {level}%" + (" (muted)" if muted else "")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return "Volume: unavailable"
