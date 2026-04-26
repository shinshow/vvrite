"""Tests for recent dictation history storage."""

import json
import os
import tempfile
import unittest

from vvrite.history_store import DictationRecord, HistoryStore


class TestHistoryStore(unittest.TestCase):
    def test_add_record_enforces_limit_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = HistoryStore(os.path.join(tmp, "history.json"), limit=2)

            store.add(
                DictationRecord(
                    text="one",
                    created_at=1.0,
                    model_key="m1",
                    output_mode="transcribe",
                    mode_key="voice",
                )
            )
            store.add(
                DictationRecord(
                    text="two",
                    created_at=2.0,
                    model_key="m1",
                    output_mode="transcribe",
                    mode_key="voice",
                )
            )
            store.add(
                DictationRecord(
                    text="three",
                    created_at=3.0,
                    model_key="m1",
                    output_mode="transcribe",
                    mode_key="voice",
                )
            )

            self.assertEqual([record.text for record in store.list()], ["three", "two"])

    def test_store_persists_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "history.json")
            store = HistoryStore(path, limit=10)
            store.add(
                DictationRecord(
                    text="hello",
                    created_at=1.0,
                    model_key="qwen",
                    output_mode="transcribe",
                    mode_key="voice",
                )
            )

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data[0]["text"], "hello")


if __name__ == "__main__":
    unittest.main()
