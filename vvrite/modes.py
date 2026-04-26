"""Lightweight output modes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutputMode:
    key: str
    title_key: str
    description_key: str


_MODES = [
    OutputMode("voice", "modes.voice.title", "modes.voice.description"),
    OutputMode("message", "modes.message.title", "modes.message.description"),
    OutputMode("note", "modes.note.title", "modes.note.description"),
    OutputMode("email", "modes.email.title", "modes.email.description"),
]


def list_modes() -> list[OutputMode]:
    return list(_MODES)


def get_mode(key: str | None) -> OutputMode:
    for mode in _MODES:
        if mode.key == key:
            return mode
    return _MODES[0]


def post_process_for_mode(mode_key: str | None, text: str) -> str:
    value = str(text or "").strip()
    mode = get_mode(mode_key)
    if mode.key == "note":
        return value.replace("\r\n", "\n")
    return value
