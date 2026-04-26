"""Local recent dictation history."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os

from vvrite import model_store


def default_history_path() -> str:
    return os.path.join(os.path.dirname(model_store.model_root()), "history.json")


@dataclass(frozen=True)
class DictationRecord:
    text: str
    created_at: float
    model_key: str
    output_mode: str
    mode_key: str


class HistoryStore:
    def __init__(self, path: str, limit: int = 10):
        self._path = path
        self._limit = max(0, int(limit))

    def list(self) -> list[DictationRecord]:
        if not os.path.exists(self._path):
            return []
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = []
        for item in data:
            try:
                records.append(DictationRecord(**item))
            except TypeError:
                continue
        return records

    def add(self, record: DictationRecord):
        if self._limit <= 0 or not record.text.strip():
            return
        records = [record] + self.list()
        records = records[: self._limit]
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump([asdict(item) for item in records], f, ensure_ascii=False, indent=2)

    def clear(self):
        if os.path.exists(self._path):
            os.unlink(self._path)
