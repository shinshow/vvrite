"""System sound playback using NSSound."""

import os
import time

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


def _sound_for_name(name: str):
    if is_custom_path(name):
        sound = NSSound.alloc().initWithContentsOfFile_byReference_(name, True)
    else:
        shared = NSSound.soundNamed_(name)
        if shared is None:
            return None
        sound = shared.copy()
    return sound


def play(name: str, volume: float = 1.0):
    """Play a sound by system name or file path, at the given volume (0.0-1.0)."""
    sound = _sound_for_name(name)
    if sound is None:
        return
    sound.setVolume_(volume)
    sound.play()


def play_and_wait(name: str, volume: float = 1.0, max_wait: float = 1.5):
    """Play a short cue and wait until it finishes or times out."""
    sound = _sound_for_name(name)
    if sound is None:
        return
    sound.setVolume_(volume)
    sound.play()
    deadline = time.monotonic() + max(0.0, float(max_wait))
    while time.monotonic() < deadline:
        try:
            if not sound.isPlaying():
                return
        except Exception:
            return
        time.sleep(0.01)
