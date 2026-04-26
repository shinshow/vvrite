"""Tests for recording start/stop sequencing."""

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from vvrite import main


class TestRecordingFlow(unittest.TestCase):
    def _delegate(self):
        delegate = main.AppDelegate.__new__(main.AppDelegate)
        delegate._prefs = SimpleNamespace(
            sound_start="Glass",
            start_volume=1.0,
            sound_stop="Purr",
            stop_volume=1.0,
            mic_device=None,
        )
        delegate._recorder = MagicMock()
        delegate._recording = False
        delegate.performSelectorOnMainThread_withObject_waitUntilDone_ = MagicMock()
        return delegate

    def test_start_recording_discards_ready_sound_before_showing_recording_ui(self):
        delegate = self._delegate()
        events = []
        delegate._recorder.start.side_effect = lambda **_kwargs: events.append(
            "recorder.start"
        )
        delegate._recorder.discard_frames.side_effect = lambda: events.append(
            "recorder.discard_frames"
        )
        delegate.performSelectorOnMainThread_withObject_waitUntilDone_.side_effect = (
            lambda selector, *_args: events.append(selector)
        )

        with patch.object(
            main.sounds,
            "play_and_wait",
            side_effect=lambda *_args: events.append("sounds.play"),
        ):
            delegate._start_recording()

        self.assertEqual(
            events,
            [
                "recorder.start",
                "sounds.play",
                "recorder.discard_frames",
                "showRecordingUI:",
            ],
        )

    def test_stop_recording_closes_microphone_before_stop_sound(self):
        delegate = self._delegate()
        delegate._recording = True
        events = []
        delegate._recorder.stop.side_effect = lambda: events.append(
            "recorder.stop"
        ) or None

        with patch.object(
            main.sounds,
            "play",
            side_effect=lambda *_args: events.append("sounds.play"),
        ):
            delegate._stop_recording()

        self.assertEqual(events, ["recorder.stop", "sounds.play"])


if __name__ == "__main__":
    unittest.main()
