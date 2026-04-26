"""Tests for global hotkey handling."""

import unittest
from unittest.mock import MagicMock, patch

import Quartz

from vvrite import hotkey


class _Prefs:
    hotkey_keycode = 49
    hotkey_modifiers = int(Quartz.kCGEventFlagMaskCommand | Quartz.kCGEventFlagMaskShift)
    retract_last_dictation_enabled = False
    retract_hotkey_keycode = 0
    retract_hotkey_modifiers = 0


class TestHotkeyManager(unittest.TestCase):
    def _manager(self, delegate):
        manager = hotkey.HotkeyManager.__new__(hotkey.HotkeyManager)
        manager._delegate = delegate
        manager._prefs = _Prefs()
        manager._tap = None
        return manager

    def test_hotkey_down_toggles_recording(self):
        delegate = MagicMock()
        manager = self._manager(delegate)

        def field_value(_event, field):
            if field == Quartz.kCGKeyboardEventKeycode:
                return _Prefs.hotkey_keycode
            if field == Quartz.kCGKeyboardEventAutorepeat:
                return 0
            return 0

        with (
            patch.object(hotkey, "CGEventGetIntegerValueField", side_effect=field_value),
            patch.object(hotkey, "CGEventGetFlags", return_value=_Prefs.hotkey_modifiers),
            patch.object(hotkey.threading, "Thread") as thread,
        ):
            result = manager._callback(None, Quartz.kCGEventKeyDown, object(), None)

        self.assertIsNone(result)
        self.assertIs(thread.call_args.kwargs["target"], delegate.toggleRecording)

    def test_hotkey_up_does_not_toggle_recording(self):
        delegate = MagicMock()
        manager = self._manager(delegate)

        def field_value(_event, field):
            if field == Quartz.kCGKeyboardEventKeycode:
                return _Prefs.hotkey_keycode
            return 0

        with (
            patch.object(hotkey, "CGEventGetIntegerValueField", side_effect=field_value),
            patch.object(hotkey, "CGEventGetFlags", return_value=0),
            patch.object(hotkey.threading, "Thread") as thread,
        ):
            result = manager._callback(None, Quartz.kCGEventKeyUp, object(), None)

        self.assertIsNotNone(result)
        thread.assert_not_called()

    def test_ignores_auto_repeat_for_recording_hotkey(self):
        delegate = MagicMock()
        manager = self._manager(delegate)

        def field_value(_event, field):
            if field == Quartz.kCGKeyboardEventKeycode:
                return _Prefs.hotkey_keycode
            if field == Quartz.kCGKeyboardEventAutorepeat:
                return 1
            return 0

        with (
            patch.object(hotkey, "CGEventGetIntegerValueField", side_effect=field_value),
            patch.object(hotkey, "CGEventGetFlags", return_value=_Prefs.hotkey_modifiers),
        ):
            result = manager._callback(None, Quartz.kCGEventKeyDown, object(), None)

        self.assertIsNone(result)
        delegate.toggleRecording.assert_not_called()


if __name__ == "__main__":
    unittest.main()
