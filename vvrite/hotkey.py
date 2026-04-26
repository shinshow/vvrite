"""Global hotkey via CGEvent tap."""

import threading

import Quartz
from Quartz import (
    CGEventTapCreate,
    CGEventMaskBit,
    CGEventGetIntegerValueField,
    CGEventGetFlags,
    CGEventTapEnable,
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    kCGSessionEventTap,
    kCGHeadInsertEventTap,
    kCGEventTapOptionDefault,
    kCGEventKeyDown,
    kCGEventTapDisabledByTimeout,
    kCGKeyboardEventKeycode,
    kCGKeyboardEventAutorepeat,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskShift,
    kCFRunLoopDefaultMode,
)
from Foundation import NSLog

from vvrite.preferences import Preferences

MODIFIER_MASK = (
    kCGEventFlagMaskCommand | kCGEventFlagMaskShift
    | Quartz.kCGEventFlagMaskControl | Quartz.kCGEventFlagMaskAlternate
)


class HotkeyManager:
    """Manages global hotkey via CGEvent tap. Not an NSObject."""

    def __init__(self, delegate):
        self._delegate = delegate
        self._prefs = Preferences()
        self._tap = None
        self._setup_tap()

    def _setup_tap(self):
        self._tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            CGEventMaskBit(kCGEventKeyDown),
            self._callback,
            None,
        )

        if self._tap is None:
            NSLog("Failed to create CGEvent tap — accessibility not granted")
            return

        source = CFMachPortCreateRunLoopSource(None, self._tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopDefaultMode)
        CGEventTapEnable(self._tap, True)

    def _callback(self, proxy, event_type, event, refcon):
        if event_type == kCGEventTapDisabledByTimeout:
            if self._tap:
                CGEventTapEnable(self._tap, True)
            return event

        if event_type == kCGEventKeyDown:
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            flags = CGEventGetFlags(event)

            target_keycode = self._prefs.hotkey_keycode
            target_mods = self._prefs.hotkey_modifiers
            retract_enabled = self._prefs.retract_last_dictation_enabled
            retract_keycode = self._prefs.retract_hotkey_keycode
            retract_mods = self._prefs.retract_hotkey_modifiers

            if keycode == target_keycode and (flags & MODIFIER_MASK) == target_mods:
                if CGEventGetIntegerValueField(event, kCGKeyboardEventAutorepeat):
                    return None
                threading.Thread(
                    target=self._delegate.toggleRecording,
                    daemon=True,
                ).start()
                return None

            if (
                retract_enabled
                and keycode == retract_keycode
                and (flags & MODIFIER_MASK) == retract_mods
            ):
                threading.Thread(
                    target=self._delegate.retractLastDictation,
                    daemon=True,
                ).start()
                return None

            # ESC (0x35) with no modifiers cancels recording
            if (
                keycode == 0x35
                and (flags & MODIFIER_MASK) == 0
                and self._delegate._recording
            ):
                threading.Thread(
                    target=self._delegate.cancelRecording,
                    daemon=True,
                ).start()
                return None

        return event
