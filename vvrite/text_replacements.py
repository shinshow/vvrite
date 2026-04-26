"""Post-transcription replacement rules."""

from __future__ import annotations


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
