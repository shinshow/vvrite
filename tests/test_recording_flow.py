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
            asr_model_key="qwen3_asr_1_7b_bf16",
        )
        delegate._recorder = MagicMock()
        delegate._overlay = MagicMock()
        delegate._status_bar = MagicMock()
        delegate._recording = False
        delegate._last_dictation_text = None
        delegate.performSelectorOnMainThread_withObject_waitUntilDone_ = MagicMock()
        return delegate

    def test_start_recording_shows_ui_after_discarding_ready_sound_frames(self):
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
            side_effect=lambda *_args, **_kwargs: events.append("sounds.play"),
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

    def test_start_recording_caps_ready_sound_wait_for_responsiveness(self):
        delegate = self._delegate()

        with patch.object(main.sounds, "play_and_wait") as mock_play:
            delegate._start_recording()

        mock_play.assert_called_once_with("Glass", 1.0, max_wait=0.35)

    def test_recording_overlay_shows_current_model(self):
        delegate = self._delegate()

        delegate.showRecordingUI_(None)

        delegate._overlay.setModelName_.assert_called_once_with("Qwen BF16")
        delegate._overlay.showRecording.assert_called_once_with()

    def test_transcribing_overlay_keeps_current_model_visible(self):
        delegate = self._delegate()

        delegate.showTranscribingUI_(None)

        delegate._overlay.setModelName_.assert_called_once_with("Qwen BF16")
        delegate._overlay.showTranscribing.assert_called_once_with()

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

    @patch("vvrite.main.paste_and_restore")
    @patch("vvrite.main.transcriber.transcribe", return_value="hello")
    def test_transcribe_and_paste_restores_clipboard_asynchronously(
        self, _mock_transcribe, mock_paste
    ):
        delegate = self._delegate()

        delegate._transcribe_and_paste("/tmp/audio.wav")

        mock_paste.assert_called_once_with("hello", async_restore=True)

    @patch("vvrite.main.paste_and_restore")
    @patch("vvrite.main.transcriber.transcribe", return_value="큐엔 모델")
    def test_transcribe_and_paste_applies_replacements(
        self, _mock_transcribe, mock_paste
    ):
        delegate = self._delegate()
        delegate._prefs.replacement_rules = "큐엔 -> Qwen"

        delegate._transcribe_and_paste("/tmp/audio.wav")

        mock_paste.assert_called_once_with("Qwen 모델", async_restore=True)
        self.assertEqual(delegate._last_dictation_text, "Qwen 모델")

    @patch("vvrite.main.paste_and_restore")
    @patch("vvrite.main.transcriber.transcribe", return_value="hello\r\nworld")
    def test_transcribe_and_paste_applies_selected_mode(
        self, _mock_transcribe, mock_paste
    ):
        delegate = self._delegate()
        delegate._prefs.selected_mode_key = "note"

        delegate._transcribe_and_paste("/tmp/audio.wav")

        mock_paste.assert_called_once_with("hello\nworld", async_restore=True)

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

    @patch("vvrite.main.NSModalResponseOK", 1)
    @patch(
        "vvrite.main.prepare_transcription_input",
        return_value="/tmp/prepared.wav",
    )
    @patch("vvrite.main.NSOpenPanel")
    def test_transcribe_file_prepares_copy_and_starts_transcription(
        self, mock_open_panel, mock_prepare
    ):
        delegate = self._delegate()
        panel = MagicMock()
        url = MagicMock()
        url.path.return_value = "/tmp/source.wav"
        panel.URL.return_value = url
        panel.runModal.return_value = 1
        mock_open_panel.openPanel.return_value = panel

        with patch.object(main.threading, "Thread") as mock_thread:
            delegate.transcribeFile_(None)

        mock_prepare.assert_called_once_with("/tmp/source.wav")
        delegate._status_bar.setStatus_.assert_called_once_with("transcribing")
        delegate._overlay.showTranscribing.assert_called_once_with()
        mock_thread.assert_called_once_with(
            target=delegate._transcribe_and_paste,
            args=("/tmp/prepared.wav",),
            daemon=True,
        )
        mock_thread.return_value.start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
