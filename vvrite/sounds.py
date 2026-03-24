"""System sound playback using NSSound."""

import os

from AppKit import NSSound

SYSTEM_SOUNDS_DIR = "/System/Library/Sounds"


def is_custom_path(name: str) -> bool:
    """Return True if name is a file path rather than a system sound name."""
    return "/" in name


def list_system_sounds() -> list[str]:
    """Return sorted list of macOS system sound names (without extension)."""
    if not os.path.isdir(SYSTEM_SOUNDS_DIR):
        return []
    names = []
    for entry in os.listdir(SYSTEM_SOUNDS_DIR):
        if entry.endswith(".aiff"):
            names.append(entry[:-5])  # strip .aiff
    return sorted(names)


def play(name: str):
    """Play a macOS system sound by name (non-blocking)."""
    sound = NSSound.soundNamed_(name)
    if sound:
        sound.play()
