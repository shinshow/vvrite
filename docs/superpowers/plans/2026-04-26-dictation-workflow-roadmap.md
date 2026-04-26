# Dictation Workflow Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safer, higher-value dictation workflow features in phases: automatic replacements, recent history, file transcription, lightweight modes, and cleanup of the existing retract-last-dictation shortcut.

**Architecture:** Keep ASR backends focused on transcription and add post-transcription behavior outside model-specific code. Store user-facing workflow state in small dedicated modules instead of expanding `main.py` and `settings.py` further. Implement each phase behind existing preferences/defaults so the app remains usable if later phases are not implemented.

**Tech Stack:** Python 3.14, PyObjC/AppKit, NSUserDefaults, local JSON files under Application Support, `unittest`, existing `vvrite.transcriber` and `vvrite.clipboard` modules.

---

## Scope And Sequencing

This plan covers five product improvements, but they should not be implemented as one large commit. Each phase produces working, testable software on its own.

**Already completed before this plan:**
- Commit `58bc1c4 feat: improve custom words management`
- Custom words now support multiline editing, `.txt/.csv` import, and `.txt/.csv` export.

**Implementation order:**
1. Automatic replacements
2. Recent dictation history
3. File transcription
4. Lightweight modes and post-processing prompts
5. Retract-last-dictation shortcut cleanup

**Primary rule:** Do not modify ASR backend behavior for UI features unless the phase explicitly needs ASR input/output changes. Most new behavior should happen after `transcriber.transcribe(...)` returns text.

---

## File Structure

### New Files

- `vvrite/text_replacements.py`
  - Parse, normalize, store, import/export, and apply post-transcription replacement rules.
  - No AppKit imports.

- `vvrite/history_store.py`
  - Store recent dictation records as JSON under `~/Library/Application Support/vvrite/history.json`.
  - Enforce a small retention cap by default.
  - No UI imports.

- `vvrite/file_transcription.py`
  - Copy selected audio/video files into temporary working files before transcription so backend cleanup never deletes user originals.
  - Own file extension validation and result formatting.

- `vvrite/modes.py`
  - Define built-in mode metadata and simple local post-processing behaviors.
  - Keep this local and deterministic until a real AI post-processing provider is selected.

### Modified Files

- `vvrite/preferences.py`
  - Add preferences for replacements, history enabled/cap, selected mode, paste behavior, and retract shortcut visibility.

- `vvrite/main.py`
  - Route transcription output through post-processing.
  - Add history insertion.
  - Add menu action handlers for file transcription and recent history.

- `vvrite/settings.py`
  - Add replacements editor.
  - Add history settings.
  - Add mode selector.
  - Move retract shortcut controls under an advanced/correction subsection.

- `vvrite/status_bar.py`
  - Add menu items for file transcription and recent history.
  - Update menu item enabled state from delegate.

- `vvrite/locales/*.py`
  - Add strings for replacements, history, file transcription, modes, and advanced correction.

- `tests/test_text_replacements.py`
  - Replacement parsing, application, import/export.

- `tests/test_history_store.py`
  - Retention, JSON persistence, disabled state.

- `tests/test_file_transcription.py`
  - Safe file copy behavior, input extension checks.

- `tests/test_modes.py`
  - Built-in mode definitions and deterministic formatting.

- Existing tests:
  - `tests/test_recording_flow.py`
  - `tests/test_settings.py`
  - `tests/test_status_bar.py`
  - `tests/test_preferences.py`
  - `tests/test_locales.py`

---

## Phase 1: Automatic Replacements

**User value:** Fix repeated ASR mistakes consistently after transcription, without relying on model prompt interpretation.

**Behavior:**
- User configures replacement rules as `source -> target`.
- Matching is case-insensitive.
- Output uses the exact target text entered by the user.
- Rules run after ASR returns text and before paste/history.
- Empty, duplicate, or malformed rules are ignored.

### Task 1: Add Replacement Rule Parser

**Files:**
- Create: `vvrite/text_replacements.py`
- Test: `tests/test_text_replacements.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for post-transcription replacement rules."""

import unittest

from vvrite.text_replacements import parse_replacements_text


class TestReplacementParsing(unittest.TestCase):
    def test_parse_replacements_accepts_arrow_and_comma_lines(self):
        text = """
        큐엔 -> Qwen
        브이라이트,vvrite
        malformed line
        큐엔 -> Qwen
        """

        rules = parse_replacements_text(text)

        self.assertEqual(
            rules,
            [
                ("큐엔", "Qwen"),
                ("브이라이트", "vvrite"),
            ],
        )

    def test_parse_replacements_ignores_empty_sides(self):
        rules = parse_replacements_text(" -> Qwen\nOpenAI -> \n")

        self.assertEqual(rules, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_text_replacements.TestReplacementParsing
```

Expected: import error because `vvrite.text_replacements` does not exist.

- [ ] **Step 3: Add parser implementation**

Create `vvrite/text_replacements.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/python -m unittest tests.test_text_replacements.TestReplacementParsing
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add vvrite/text_replacements.py tests/test_text_replacements.py
git commit -m "feat: add replacement rule parsing"
```

### Task 2: Apply Replacement Rules To Transcribed Text

**Files:**
- Modify: `vvrite/text_replacements.py`
- Test: `tests/test_text_replacements.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_text_replacements.py`:

```python
from vvrite.text_replacements import apply_replacements


class TestReplacementApplication(unittest.TestCase):
    def test_apply_replacements_is_case_insensitive(self):
        result = apply_replacements(
            "큐엔 모델과 OPEN AI를 사용합니다.",
            [("큐엔", "Qwen"), ("open ai", "OpenAI")],
        )

        self.assertEqual(result, "Qwen 모델과 OpenAI를 사용합니다.")

    def test_apply_replacements_respects_word_boundaries_for_ascii(self):
        result = apply_replacements(
            "todo and methodology",
            [("todo", "TODO")],
        )

        self.assertEqual(result, "TODO and methodology")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_text_replacements.TestReplacementApplication
```

Expected: import error for `apply_replacements`.

- [ ] **Step 3: Add application implementation**

Update `vvrite/text_replacements.py`:

```python
import re


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
```

- [ ] **Step 4: Run replacement tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_text_replacements
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add vvrite/text_replacements.py tests/test_text_replacements.py
git commit -m "feat: apply transcription replacements"
```

### Task 3: Persist Replacement Rules In Preferences

**Files:**
- Modify: `vvrite/preferences.py`
- Modify: `tests/test_preferences.py`

- [ ] **Step 1: Write the failing test**

Add `replacement_rules` to `_TEST_KEYS` in `tests/test_preferences.py`, then add:

```python
    def test_default_replacement_rules(self):
        from vvrite.preferences import Preferences

        prefs = Preferences()

        self.assertEqual(prefs.replacement_rules, "")

    def test_set_replacement_rules(self):
        from vvrite.preferences import Preferences

        prefs = Preferences()
        prefs.replacement_rules = "큐엔 -> Qwen"

        self.assertEqual(prefs.replacement_rules, "큐엔 -> Qwen")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_preferences.TestPreferences.test_default_replacement_rules tests.test_preferences.TestPreferences.test_set_replacement_rules
```

Expected: `AttributeError` for `replacement_rules`.

- [ ] **Step 3: Add preference**

In `vvrite/preferences.py`, add to `_DEFAULTS`:

```python
    "replacement_rules": "",
```

Add property:

```python
    @property
    def replacement_rules(self) -> str:
        return str(self._get("replacement_rules"))

    @replacement_rules.setter
    def replacement_rules(self, value: str):
        self._set("replacement_rules", value)
```

- [ ] **Step 4: Run preferences tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_preferences
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add vvrite/preferences.py tests/test_preferences.py
git commit -m "feat: persist replacement rules"
```

### Task 4: Route Dictation Output Through Replacements

**Files:**
- Modify: `vvrite/main.py`
- Test: `tests/test_recording_flow.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_recording_flow.py`:

```python
    @patch("vvrite.main.paste_and_restore")
    @patch("vvrite.main.transcriber.transcribe", return_value="큐엔 모델")
    def test_transcribe_and_paste_applies_replacements(self, _mock_transcribe, mock_paste):
        delegate = self._delegate()
        delegate._prefs.replacement_rules = "큐엔 -> Qwen"

        delegate._transcribe_and_paste("/tmp/audio.wav")

        mock_paste.assert_called_once_with("Qwen 모델", async_restore=True)
        self.assertEqual(delegate._last_dictation_text, "Qwen 모델")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_recording_flow.TestRecordingFlow.test_transcribe_and_paste_applies_replacements
```

Expected: paste called with unmodified text.

- [ ] **Step 3: Add post-processing in `main.py`**

Add import:

```python
from vvrite.text_replacements import apply_replacements, parse_replacements_text
```

Add helper:

```python
def _post_process_text(text: str, prefs: Preferences) -> str:
    rules = parse_replacements_text(getattr(prefs, "replacement_rules", ""))
    return apply_replacements(text, rules).strip()
```

Update `_transcribe_and_paste` after transcription:

```python
            text = transcriber.transcribe(raw_path, self._prefs)
            text = _post_process_text(text, self._prefs)
            if text:
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_recording_flow tests.test_text_replacements
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add vvrite/main.py tests/test_recording_flow.py
git commit -m "feat: apply replacements before paste"
```

### Task 5: Add Replacement Rules Settings UI

**Files:**
- Modify: `vvrite/settings.py`
- Modify: `vvrite/locales/*.py`
- Modify: `tests/test_settings.py`
- Modify: `tests/test_locales.py`

- [ ] **Step 1: Write tests for settings save behavior**

Add to `tests/test_settings.py`:

```python
class TestReplacementRulesSettings(unittest.TestCase):
    def setUp(self):
        self.controller = SettingsWindowController.alloc().init()
        self.controller._prefs = MagicMock()
        self.controller._replacement_rules_text_view = MagicMock()

    def test_save_replacement_rules_normalizes_valid_lines(self):
        self.controller._replacement_rules_text_view.string.return_value = (
            "큐엔 -> Qwen\n브이라이트,vvrite\nbad"
        )

        self.controller._save_replacement_rules()

        self.assertEqual(
            self.controller._prefs.replacement_rules,
            "큐엔 -> Qwen\n브이라이트 -> vvrite",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m unittest tests.test_settings.TestReplacementRulesSettings
```

Expected: `_save_replacement_rules` missing.

- [ ] **Step 3: Add formatting helper**

In `vvrite/text_replacements.py`:

```python
def format_replacements_text(text: str) -> str:
    return "\n".join(
        f"{source} -> {target}"
        for source, target in parse_replacements_text(text)
    )
```

- [ ] **Step 4: Add settings controller state**

In `SettingsWindowController.initWithPreferences_`, add:

```python
        self._replacement_rules_text_view = None
```

- [ ] **Step 5: Add settings UI section**

Place the section after Custom Words:

```python
        # --- Replacements ---
        y -= 40
        label = NSTextField.labelWithString_(t("settings.replacements.title"))
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 86
        replacement_scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, y, 360, 78)
        )
        replacement_scroll.setHasVerticalScroller_(True)
        replacement_scroll.setAutohidesScrollers_(True)
        replacement_scroll.setBorderType_(1)
        self._replacement_rules_text_view = NSTextView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 360, 78)
        )
        self._replacement_rules_text_view.setString_(
            format_replacements_text(self._prefs.replacement_rules)
        )
        self._replacement_rules_text_view.setFont_(NSFont.systemFontOfSize_(12.0))
        self._replacement_rules_text_view.setDelegate_(self)
        replacement_scroll.setDocumentView_(self._replacement_rules_text_view)
        content.addSubview_(replacement_scroll)

        y -= 20
        hint = NSTextField.labelWithString_(t("settings.replacements.hint"))
        hint.setFrame_(NSMakeRect(20, y, 360, 16))
        hint.setFont_(NSFont.systemFontOfSize_(11.0))
        hint.setTextColor_(NSColor.secondaryLabelColor())
        content.addSubview_(hint)
```

Increase `SETTINGS_WINDOW_HEIGHT` enough to prevent overlap:

```python
SETTINGS_WINDOW_HEIGHT = 1060
```

- [ ] **Step 6: Add save methods**

In `settings.py`:

```python
    def _save_replacement_rules(self):
        if self._replacement_rules_text_view is None:
            return
        value = format_replacements_text(str(self._replacement_rules_text_view.string()))
        self._prefs.replacement_rules = value
        self._replacement_rules_text_view.setString_(value)
```

Update `windowWillClose_`:

```python
        self._save_replacement_rules()
```

Update `textDidEndEditing_`:

```python
        if notification.object() == self._replacement_rules_text_view:
            self._save_replacement_rules()
```

- [ ] **Step 7: Add locale keys**

Add this group to `settings` in all locale files:

```python
        "replacements": {
            "title": "Replacements",
            "hint": "One rule per line, for example: 큐엔 -> Qwen",
        },
```

Use translated text for `en.py` and `ko.py`; other locale files may use English if translation quality is uncertain, but keys must exist in every file.

- [ ] **Step 8: Update locale tests**

In `tests/test_locales.py`, add:

```python
        self.assertIn("replacements", s)
        for key in ["title", "hint"]:
            self.assertIn(key, s["replacements"], f"Missing settings.replacements.{key}")
```

- [ ] **Step 9: Run settings and locale tests**

Run:

```bash
.venv/bin/python -m unittest tests.test_settings tests.test_locales tests.test_text_replacements
```

Expected: `OK`.

- [ ] **Step 10: Run settings window smoke test**

Run:

```bash
.venv/bin/python -c $'from AppKit import NSApplication\napp=NSApplication.sharedApplication()\nfrom vvrite.preferences import Preferences\nfrom vvrite.settings import SettingsWindowController\nwc=SettingsWindowController.alloc().initWithPreferences_(Preferences())\nprint("settings window built", wc is not None)\n'
```

Expected: `settings window built True`.

- [ ] **Step 11: Commit**

```bash
git add vvrite/settings.py vvrite/text_replacements.py vvrite/locales tests
git commit -m "feat: add replacement rules settings"
```

---

## Phase 2: Recent Dictation History

**User value:** Recover, copy, and inspect recent dictations without relying on unsafe Delete-based undo.

**Behavior:**
- Keep recent text results locally.
- Default cap: 10 items.
- Store text, timestamp, selected ASR model, output mode, and mode key.
- Do not store raw audio in this phase.
- Add menu entries for “Recent Dictations” and “Copy Last Dictation”.

### Task 6: Add History Store

**Files:**
- Create: `vvrite/history_store.py`
- Test: `tests/test_history_store.py`

- [ ] **Step 1: Write failing tests**

```python
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

            store.add(DictationRecord(text="one", created_at=1.0, model_key="m1", output_mode="transcribe", mode_key="voice"))
            store.add(DictationRecord(text="two", created_at=2.0, model_key="m1", output_mode="transcribe", mode_key="voice"))
            store.add(DictationRecord(text="three", created_at=3.0, model_key="m1", output_mode="transcribe", mode_key="voice"))

            self.assertEqual([record.text for record in store.list()], ["three", "two"])

    def test_store_persists_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "history.json")
            store = HistoryStore(path, limit=10)
            store.add(DictationRecord(text="hello", created_at=1.0, model_key="qwen", output_mode="transcribe", mode_key="voice"))

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data[0]["text"], "hello")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m unittest tests.test_history_store
```

Expected: import error.

- [ ] **Step 3: Implement `history_store.py`**

```python
"""Local recent dictation history."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os


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
```

- [ ] **Step 4: Run history tests**

```bash
.venv/bin/python -m unittest tests.test_history_store
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add vvrite/history_store.py tests/test_history_store.py
git commit -m "feat: add recent dictation history store"
```

### Task 7: Add History Preferences And App Store Path

**Files:**
- Modify: `vvrite/preferences.py`
- Modify: `tests/test_preferences.py`
- Modify: `vvrite/model_store.py` or create helper inside `history_store.py`

- [ ] **Step 1: Add failing preference tests**

Add keys to `_TEST_KEYS`:

```python
    "history_enabled",
    "history_limit",
```

Add tests:

```python
    def test_default_history_preferences(self):
        from vvrite.preferences import Preferences

        prefs = Preferences()

        self.assertTrue(prefs.history_enabled)
        self.assertEqual(prefs.history_limit, 10)
```

- [ ] **Step 2: Run tests to verify failure**

```bash
.venv/bin/python -m unittest tests.test_preferences.TestPreferences.test_default_history_preferences
```

Expected: missing properties.

- [ ] **Step 3: Add defaults and properties**

In `preferences.py`:

```python
    "history_enabled": True,
    "history_limit": 10,
```

Properties:

```python
    @property
    def history_enabled(self) -> bool:
        return bool(self._get("history_enabled"))

    @history_enabled.setter
    def history_enabled(self, value: bool):
        self._set("history_enabled", value)

    @property
    def history_limit(self) -> int:
        return int(self._get("history_limit"))

    @history_limit.setter
    def history_limit(self, value: int):
        self._set("history_limit", max(0, int(value)))
```

- [ ] **Step 4: Add default history path helper**

In `history_store.py`:

```python
from vvrite import model_store


def default_history_path() -> str:
    return os.path.join(model_store.app_support_dir(), "history.json")
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/python -m unittest tests.test_preferences tests.test_history_store
```

Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add vvrite/preferences.py vvrite/history_store.py tests/test_preferences.py tests/test_history_store.py
git commit -m "feat: add history preferences"
```

### Task 8: Save Dictations To History

**Files:**
- Modify: `vvrite/main.py`
- Test: `tests/test_recording_flow.py`

- [ ] **Step 1: Write failing test**

```python
    @patch("vvrite.main.HistoryStore")
    @patch("vvrite.main.time.time", return_value=123.0)
    @patch("vvrite.main.paste_and_restore")
    @patch("vvrite.main.transcriber.transcribe", return_value="hello")
    def test_transcribe_and_paste_saves_history(
        self, _mock_transcribe, _mock_paste, _mock_time, mock_store_class
    ):
        store = MagicMock()
        mock_store_class.return_value = store
        delegate = self._delegate()
        delegate._prefs.history_enabled = True
        delegate._prefs.history_limit = 10
        delegate._prefs.asr_model_key = "qwen3_asr_1_7b_8bit"
        delegate._prefs.output_mode = "transcribe"
        delegate._prefs.selected_mode_key = "voice"

        delegate._transcribe_and_paste("/tmp/audio.wav")

        record = store.add.call_args.args[0]
        self.assertEqual(record.text, "hello")
        self.assertEqual(record.created_at, 123.0)
```

- [ ] **Step 2: Run test to verify failure**

```bash
.venv/bin/python -m unittest tests.test_recording_flow.TestRecordingFlow.test_transcribe_and_paste_saves_history
```

Expected: `HistoryStore` import or call missing.

- [ ] **Step 3: Add history write**

In `main.py`, import:

```python
import time
from vvrite.history_store import DictationRecord, HistoryStore, default_history_path
```

Add helper:

```python
    def _save_history_record(self, text: str):
        if not self._prefs.history_enabled:
            return
        store = HistoryStore(default_history_path(), self._prefs.history_limit)
        store.add(
            DictationRecord(
                text=text,
                created_at=time.time(),
                model_key=self._prefs.asr_model_key,
                output_mode=self._prefs.output_mode,
                mode_key=getattr(self._prefs, "selected_mode_key", "voice"),
            )
        )
```

Call after `_last_dictation_text = text`:

```python
                self._save_history_record(text)
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m unittest tests.test_recording_flow tests.test_history_store
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add vvrite/main.py tests/test_recording_flow.py
git commit -m "feat: save recent dictations"
```

### Task 9: Add History Menu Actions

**Files:**
- Modify: `vvrite/status_bar.py`
- Modify: `vvrite/main.py`
- Modify: `vvrite/locales/*.py`
- Test: `tests/test_status_bar.py`

- [ ] **Step 1: Write failing status bar test**

```python
    def test_menu_contains_recent_history_actions(self):
        delegate = MagicMock()
        delegate._prefs.hotkey_keycode = 0x31
        delegate._prefs.hotkey_modifiers = 1 << 19

        controller = StatusBarController.alloc().initWithDelegate_(delegate)

        titles = [
            controller._menu.itemAtIndex_(i).title()
            for i in range(controller._menu.numberOfItems())
        ]
        self.assertIn("Copy Last Dictation", titles)
        self.assertIn("Recent Dictations...", titles)
```

- [ ] **Step 2: Run test to verify failure**

```bash
.venv/bin/python -m unittest tests.test_status_bar
```

Expected: menu titles missing.

- [ ] **Step 3: Add menu items**

In `status_bar.py`, after microphone display and before settings:

```python
        self._copy_last_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("menu.copy_last_dictation"), "copyLastDictation:", ""
        )
        self._copy_last_item.setTarget_(self._delegate)
        self._menu.addItem_(self._copy_last_item)

        history_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("menu.recent_dictations"), "showRecentDictations:", ""
        )
        history_item.setTarget_(self._delegate)
        self._menu.addItem_(history_item)
```

- [ ] **Step 4: Add delegate actions**

In `main.py`:

```python
    @objc.typedSelector(b"v@:@")
    def copyLastDictation_(self, sender):
        if self._last_dictation_text:
            from vvrite.clipboard import _set_text
            _set_text(self._last_dictation_text)

    @objc.typedSelector(b"v@:@")
    def showRecentDictations_(self, sender):
        records = HistoryStore(default_history_path(), self._prefs.history_limit).list()
        message = "\n\n".join(record.text for record in records[:10]) or t("history.empty")
        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("history.title"))
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_(t("common.ok"))
        NSApp.activateIgnoringOtherApps_(True)
        alert.runModal()
```

- [ ] **Step 5: Add locale keys**

Add to `menu` in every locale file:

```python
        "copy_last_dictation": "Copy Last Dictation",
        "recent_dictations": "Recent Dictations...",
```

Add top-level `history` group in every locale file:

```python
    "history": {
        "title": "Recent Dictations",
        "empty": "No recent dictations.",
    },
```

- [ ] **Step 6: Run tests**

```bash
.venv/bin/python -m unittest tests.test_status_bar tests.test_locales
```

Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
git add vvrite/status_bar.py vvrite/main.py vvrite/locales tests
git commit -m "feat: add recent dictation menu actions"
```

---

## Phase 3: File Transcription

**User value:** Transcribe existing audio/video recordings without starting a live recording.

**Critical safety issue:** Current backend implementations may delete input paths after transcription. File transcription must copy selected user files into a temporary working file before passing them to `transcriber.transcribe(...)`.

### Task 10: Add Safe File Preparation

**Files:**
- Create: `vvrite/file_transcription.py`
- Test: `tests/test_file_transcription.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for external file transcription helpers."""

import os
import tempfile
import unittest

from vvrite.file_transcription import prepare_transcription_input, is_supported_media_file


class TestFileTranscriptionHelpers(unittest.TestCase):
    def test_supported_media_extensions(self):
        self.assertTrue(is_supported_media_file("/tmp/audio.wav"))
        self.assertTrue(is_supported_media_file("/tmp/audio.mp3"))
        self.assertTrue(is_supported_media_file("/tmp/video.mp4"))
        self.assertFalse(is_supported_media_file("/tmp/note.txt"))

    def test_prepare_transcription_input_copies_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "source.wav")
            with open(source, "wb") as f:
                f.write(b"audio")

            prepared = prepare_transcription_input(source)

            self.assertNotEqual(prepared, source)
            self.assertTrue(os.path.exists(source))
            with open(prepared, "rb") as f:
                self.assertEqual(f.read(), b"audio")
```

- [ ] **Step 2: Run test to verify failure**

```bash
.venv/bin/python -m unittest tests.test_file_transcription
```

Expected: import error.

- [ ] **Step 3: Implement helper**

```python
"""Helpers for transcribing existing media files."""

from __future__ import annotations

import os
import shutil
import tempfile

SUPPORTED_MEDIA_EXTENSIONS = {".wav", ".mp3", ".m4a", ".mp4", ".caf", ".aiff", ".flac"}


def is_supported_media_file(path: str) -> bool:
    return os.path.splitext(str(path))[1].lower() in SUPPORTED_MEDIA_EXTENSIONS


def prepare_transcription_input(path: str) -> str:
    if not is_supported_media_file(path):
        raise ValueError(f"Unsupported media file: {path}")
    suffix = os.path.splitext(path)[1].lower()
    fd, dest = tempfile.mkstemp(prefix="vvrite_file_", suffix=suffix)
    os.close(fd)
    shutil.copyfile(path, dest)
    return dest
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m unittest tests.test_file_transcription
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add vvrite/file_transcription.py tests/test_file_transcription.py
git commit -m "feat: prepare safe file transcription inputs"
```

### Task 11: Add Menu-Based File Transcription

**Files:**
- Modify: `vvrite/status_bar.py`
- Modify: `vvrite/main.py`
- Modify: `vvrite/locales/*.py`
- Test: `tests/test_status_bar.py`
- Test: `tests/test_recording_flow.py`

- [ ] **Step 1: Add menu test**

```python
    def test_menu_contains_transcribe_file_action(self):
        delegate = MagicMock()
        delegate._prefs.hotkey_keycode = 0x31
        delegate._prefs.hotkey_modifiers = 1 << 19

        controller = StatusBarController.alloc().initWithDelegate_(delegate)

        titles = [
            controller._menu.itemAtIndex_(i).title()
            for i in range(controller._menu.numberOfItems())
        ]
        self.assertIn("Transcribe File...", titles)
```

- [ ] **Step 2: Run test to verify failure**

```bash
.venv/bin/python -m unittest tests.test_status_bar
```

Expected: menu title missing.

- [ ] **Step 3: Add menu item**

In `status_bar.py`:

```python
        transcribe_file_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("menu.transcribe_file"), "transcribeFile:", ""
        )
        transcribe_file_item.setTarget_(self._delegate)
        self._menu.addItem_(transcribe_file_item)
```

- [ ] **Step 4: Add AppDelegate file picker**

In `main.py`, import:

```python
from AppKit import NSModalResponseOK, NSOpenPanel
from vvrite.file_transcription import prepare_transcription_input
```

Add action:

```python
    @objc.typedSelector(b"v@:@")
    def transcribeFile_(self, sender):
        panel = NSOpenPanel.openPanel()
        panel.setAllowedFileTypes_(["wav", "mp3", "m4a", "mp4", "caf", "aiff", "flac"])
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setTitle_(t("file_transcription.choose_file"))
        response = panel.runModal()
        if response != NSModalResponseOK:
            return
        source_path = str(panel.URL().path())
        prepared_path = prepare_transcription_input(source_path)
        self._status_bar.setStatus_("transcribing")
        self._overlay.showTranscribing()
        threading.Thread(
            target=self._transcribe_and_paste,
            args=(prepared_path,),
            daemon=True,
        ).start()
```

The test for this method should mock `panel.runModal()` to return `NSModalResponseOK` and should verify that `prepare_transcription_input(source_path)` is called before `_transcribe_and_paste`.

- [ ] **Step 5: Add locale keys**

Add to every `menu`:

```python
        "transcribe_file": "Transcribe File...",
```

Add top-level group:

```python
    "file_transcription": {
        "choose_file": "Choose audio or video file",
    },
```

- [ ] **Step 6: Run focused tests**

```bash
.venv/bin/python -m unittest tests.test_status_bar tests.test_file_transcription tests.test_locales
```

Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
git add vvrite/status_bar.py vvrite/main.py vvrite/file_transcription.py vvrite/locales tests
git commit -m "feat: add file transcription menu action"
```

---

## Phase 4: Lightweight Modes

**User value:** Let users choose what kind of output they want without building a full cloud AI system.

**Initial mode set:**
- `voice`: exact transcription, current behavior
- `message`: trim whitespace and keep concise punctuation only
- `note`: preserve paragraphs and avoid chatty closings
- `email`: local deterministic wrapper is limited; it should not invent content

**Boundary:** Do not promise “AI rewriting” until a real post-processing model/provider is selected. This phase introduces the mode data model and UI, with conservative deterministic processing.

### Task 12: Define Mode Registry

**Files:**
- Create: `vvrite/modes.py`
- Test: `tests/test_modes.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for output modes."""

import unittest

from vvrite.modes import get_mode, list_modes, post_process_for_mode


class TestModes(unittest.TestCase):
    def test_default_modes_exist(self):
        keys = [mode.key for mode in list_modes()]

        self.assertEqual(keys, ["voice", "message", "note", "email"])

    def test_unknown_mode_falls_back_to_voice(self):
        self.assertEqual(get_mode("missing").key, "voice")

    def test_message_mode_trims_text(self):
        self.assertEqual(post_process_for_mode("message", " hello  "), "hello")
```

- [ ] **Step 2: Run test to verify failure**

```bash
.venv/bin/python -m unittest tests.test_modes
```

Expected: import error.

- [ ] **Step 3: Implement `modes.py`**

```python
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
```

- [ ] **Step 4: Run mode tests**

```bash
.venv/bin/python -m unittest tests.test_modes
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add vvrite/modes.py tests/test_modes.py
git commit -m "feat: add lightweight output modes"
```

### Task 13: Add Selected Mode Preference And Settings UI

**Files:**
- Modify: `vvrite/preferences.py`
- Modify: `vvrite/settings.py`
- Modify: `vvrite/locales/*.py`
- Modify: `tests/test_preferences.py`
- Modify: `tests/test_settings.py`
- Modify: `tests/test_locales.py`

- [ ] **Step 1: Add preference tests**

In `tests/test_preferences.py`, add `selected_mode_key` to `_TEST_KEYS`, then:

```python
    def test_default_selected_mode_key(self):
        from vvrite.preferences import Preferences

        prefs = Preferences()

        self.assertEqual(prefs.selected_mode_key, "voice")
```

- [ ] **Step 2: Run test to verify failure**

```bash
.venv/bin/python -m unittest tests.test_preferences.TestPreferences.test_default_selected_mode_key
```

Expected: missing property.

- [ ] **Step 3: Add preference**

In `_DEFAULTS`:

```python
    "selected_mode_key": "voice",
```

Property:

```python
    @property
    def selected_mode_key(self) -> str:
        return str(self._get("selected_mode_key"))

    @selected_mode_key.setter
    def selected_mode_key(self, value: str):
        self._set("selected_mode_key", value)
```

- [ ] **Step 4: Add settings popup**

In `settings.py`, import:

```python
from vvrite.modes import get_mode, list_modes
```

Add controller field:

```python
        self._mode_popup = None
```

Add UI section near Model:

```python
        # --- Mode ---
        y -= 40
        label = NSTextField.labelWithString_(t("settings.mode.title"))
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 30
        self._mode_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(20, y, 360, 24), False
        )
        for mode in list_modes():
            self._mode_popup.addItemWithTitle_(t(mode.title_key))
        selected_key = get_mode(self._prefs.selected_mode_key).key
        for index, mode in enumerate(list_modes()):
            if mode.key == selected_key:
                self._mode_popup.selectItemAtIndex_(index)
                break
        self._mode_popup.setTarget_(self)
        self._mode_popup.setAction_("modeChanged:")
        content.addSubview_(self._mode_popup)
```

Add action:

```python
    @objc.typedSelector(b"v@:@")
    def modeChanged_(self, sender):
        self._prefs.selected_mode_key = list_modes()[sender.indexOfSelectedItem()].key
```

- [ ] **Step 5: Add locale keys**

In every locale file:

```python
        "mode": {
            "title": "Mode",
        },
```

Top-level:

```python
    "modes": {
        "voice": {"title": "Voice", "description": "Paste transcription as spoken."},
        "message": {"title": "Message", "description": "Short text for chats."},
        "note": {"title": "Note", "description": "Clean text for notes."},
        "email": {"title": "Email", "description": "Plain email-friendly text."},
    },
```

- [ ] **Step 6: Run tests**

```bash
.venv/bin/python -m unittest tests.test_preferences tests.test_settings tests.test_locales tests.test_modes
```

Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
git add vvrite/preferences.py vvrite/settings.py vvrite/locales tests
git commit -m "feat: add mode selection"
```

### Task 14: Apply Mode Post-Processing

**Files:**
- Modify: `vvrite/main.py`
- Test: `tests/test_recording_flow.py`

- [ ] **Step 1: Add failing test**

```python
    @patch("vvrite.main.paste_and_restore")
    @patch("vvrite.main.transcriber.transcribe", return_value=" hello ")
    def test_transcribe_and_paste_applies_selected_mode(self, _mock_transcribe, mock_paste):
        delegate = self._delegate()
        delegate._prefs.selected_mode_key = "message"

        delegate._transcribe_and_paste("/tmp/audio.wav")

        mock_paste.assert_called_once_with("hello", async_restore=True)
```

- [ ] **Step 2: Run test to verify failure**

```bash
.venv/bin/python -m unittest tests.test_recording_flow.TestRecordingFlow.test_transcribe_and_paste_applies_selected_mode
```

Expected: untrimmed text pasted.

- [ ] **Step 3: Update post-processing helper**

In `main.py`, import:

```python
from vvrite.modes import post_process_for_mode
```

Update `_post_process_text`:

```python
def _post_process_text(text: str, prefs: Preferences) -> str:
    value = post_process_for_mode(getattr(prefs, "selected_mode_key", "voice"), text)
    rules = parse_replacements_text(getattr(prefs, "replacement_rules", ""))
    return apply_replacements(value, rules).strip()
```

- [ ] **Step 4: Run focused tests**

```bash
.venv/bin/python -m unittest tests.test_recording_flow tests.test_modes tests.test_text_replacements
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add vvrite/main.py tests/test_recording_flow.py
git commit -m "feat: apply selected output mode"
```

---

## Phase 5: Retract Shortcut Cleanup

**User value:** Reduce confusing settings surface while retaining a power-user recovery shortcut.

**Decision:** Do not add a menu item named “Delete Last Dictation.” Keep the existing shortcut disabled by default and move it under an advanced correction label. Recent history and copy actions should become the safer, visible recovery path.

### Task 15: Rename And Move Retract Controls To Advanced Correction

**Files:**
- Modify: `vvrite/settings.py`
- Modify: `vvrite/onboarding.py`
- Modify: `vvrite/locales/*.py`
- Modify: `tests/test_locales.py`

- [ ] **Step 1: Update locale test expectations**

In `tests/test_locales.py`, add to `settings.correction` keys:

```python
            "advanced_title",
            "retract_enable",
            "retract_hint",
```

- [ ] **Step 2: Run locale test to verify failure**

```bash
.venv/bin/python -m unittest tests.test_locales.TestEnglishStringsCompleteness.test_settings_keys
```

Expected: missing keys.

- [ ] **Step 3: Add clearer locale strings**

In `en.py`:

```python
        "correction": {
            "title": "Correction",
            "advanced_title": "Advanced Correction",
            "enable": "Enable retract last dictation shortcut",
            "retract_enable": "Enable delete-by-keystroke shortcut",
            "hint": "Deletes the most recently pasted dictation result",
            "retract_hint": "Power-user shortcut. It sends Delete keypresses and only works safely right after pasting.",
        },
```

In `ko.py`:

```python
        "correction": {
            "title": "수정",
            "advanced_title": "고급 수정",
            "enable": "마지막 받아쓰기 취소 단축키 활성화",
            "retract_enable": "Delete 키 방식 삭제 단축키 활성화",
            "hint": "가장 최근에 붙여넣은 받아쓰기 결과를 삭제합니다",
            "retract_hint": "고급 사용자용입니다. Delete 키를 반복 전송하므로 붙여넣은 직후에만 안전하게 동작합니다.",
        },
```

Add equivalent keys to all other locale files, using English fallback text if translation quality is uncertain.

- [ ] **Step 4: Update settings labels**

In `settings.py`, change correction section label:

```python
        label = NSTextField.labelWithString_(t("settings.correction.advanced_title"))
```

Change checkbox title:

```python
        self._retract_checkbox.setTitle_(t("settings.correction.retract_enable"))
```

Change hint:

```python
        hint = NSTextField.labelWithString_(t("settings.correction.retract_hint"))
```

- [ ] **Step 5: Keep onboarding behavior unchanged**

Do not change `vvrite/onboarding.py` in this phase. The cleanup is limited to making the Settings copy clearer while preserving the current onboarding flow.

- [ ] **Step 6: Run tests**

```bash
.venv/bin/python -m unittest tests.test_locales tests.test_settings
```

Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
git add vvrite/settings.py vvrite/locales tests/test_locales.py
git commit -m "chore: clarify retract shortcut settings"
```

---

## Final Verification

Run these commands after all phases:

```bash
.venv/bin/python -m unittest discover tests
.venv/bin/python -m compileall -q vvrite tests
.venv/bin/python -c $'from AppKit import NSApplication\napp=NSApplication.sharedApplication()\nfrom vvrite.preferences import Preferences\nfrom vvrite.settings import SettingsWindowController\nfrom vvrite.overlay import OverlayController\nwc=SettingsWindowController.alloc().initWithPreferences_(Preferences())\nov=OverlayController.alloc().init()\nprint("ui objects built", wc is not None, ov is not None)\n'
```

Expected:
- unittest reports all tests passing.
- compileall exits with code 0.
- UI smoke command prints `ui objects built True True`.

For release validation, run:

```bash
./scripts/build.sh --local
```

Expected:
- Local app build completes.
- DMG is created under `dist/`.

---

## Risk Notes

- **Replacement rules can over-correct text.** Use word boundaries for ASCII sources and case-insensitive exact phrase matching for all rules.
- **History stores private text.** Keep a low default cap, make it visible in settings, and provide a clear action in a later privacy cleanup to clear history.
- **File transcription must protect originals.** Always copy selected files before passing them to existing ASR backends.
- **Modes are not AI rewriting yet.** Keep mode labels honest until a real LLM post-processing provider exists.
- **Retract shortcut is inherently unsafe after cursor movement.** Do not make it more prominent than history/copy actions.

---

## Self-Review

**Spec coverage:** The plan covers automatic replacements, recent history, file transcription, lightweight modes, and retract shortcut cleanup.

**Placeholder scan:** No task relies on an unspecified function name. Every new function mentioned is created in an earlier or same task.

**Type consistency:** Preferences use string/bool/int properties matching NSUserDefaults patterns already used in `preferences.py`. History records are dataclasses persisted as JSON dictionaries. Mode keys are strings with `"voice"` as the fallback.
