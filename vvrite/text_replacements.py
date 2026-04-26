"""Post-transcription replacement rules."""

from __future__ import annotations

import re


def parse_replacements_text(text: str) -> list[tuple[str, str]]:
    """Parse replacement rules from newline text.

    Supported line formats:
    - source -> target
    - source,target
    """
    rules: list[tuple[str, str]] = []
    seen: set[str] = set()

    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "->" in line:
            source, target = line.split("->", 1)
        elif "," in line:
            source, target = line.split(",", 1)
        else:
            continue
        source = source.strip()
        target = target.strip()
        key = source.casefold()
        if not source or not target or key in seen:
            continue
        seen.add(key)
        rules.append((source, target))

    return rules


def _pattern_for_source(source: str) -> re.Pattern[str]:
    escaped = re.escape(source)
    if source.isascii() and any(ch.isalnum() for ch in source):
        escaped = rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
    return re.compile(escaped, re.IGNORECASE)


def apply_replacements(text: str, rules: list[tuple[str, str]]) -> str:
    """Apply replacement rules to transcription text."""
    result = str(text or "")
    for source, target in rules:
        if not source:
            continue
        result = _pattern_for_source(source).sub(target, result)
    return result


def format_replacements_text(text: str) -> str:
    """Return normalized replacement rules, one source -> target rule per line."""
    return "\n".join(
        f"{source} -> {target}"
        for source, target in parse_replacements_text(text)
    )
