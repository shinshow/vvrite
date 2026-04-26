"""Tests for settings sound customization behavior."""

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from vvrite.audio_devices import AudioInputDevice
from vvrite.settings import SettingsWindowController


class TestCustomSoundPanelResult(unittest.TestCase):
    def setUp(self):
        self.controller = SettingsWindowController.alloc().init()
        self.controller._prefs = MagicMock()
        self.controller._prefs.start_volume = 0.4
        self.controller._prefs.stop_volume = 0.6
        self.controller._populate_sounds = MagicMock()

    @patch("vvrite.settings.sounds.play")
    def test_handle_custom_sound_panel_result_saves_start_sound(self, mock_play):
        panel = MagicMock()
        panel.URL.return_value.path.return_value = "/Users/foo/start.wav"

        self.controller._handle_custom_sound_panel_result(1, panel, True)

        self.assertEqual(self.controller._prefs.sound_start, "/Users/foo/start.wav")
        mock_play.assert_called_once_with("/Users/foo/start.wav", 0.4)
        self.controller._populate_sounds.assert_called_once()

    @patch("vvrite.settings.sounds.play")
    def test_handle_custom_sound_panel_result_cancel_keeps_existing_value(self, mock_play):
        self.controller._prefs.sound_stop = "Purr"
        panel = MagicMock()

        self.controller._handle_custom_sound_panel_result(0, panel, False)

        self.assertEqual(self.controller._prefs.sound_stop, "Purr")
        mock_play.assert_not_called()
        self.controller._populate_sounds.assert_called_once()


class TestOpenCustomSoundPanel(unittest.TestCase):
    def setUp(self):
        self.controller = SettingsWindowController.alloc().init()
        self.controller._window = MagicMock()
        self.controller._handle_custom_sound_panel_result = MagicMock()

    @patch("vvrite.settings.NSOpenPanel")
    @patch("vvrite.settings.NSApp")
    def test_open_custom_sound_panel_uses_sheet_for_window(self, mock_app, mock_open_panel):
        panel = MagicMock()
        mock_open_panel.openPanel.return_value = panel

        self.controller._open_custom_sound_panel(True)

        mock_app.activateIgnoringOtherApps_.assert_called_once_with(True)
        self.controller._window.makeKeyAndOrderFront_.assert_called_once_with(None)
        panel.setAllowedFileTypes_.assert_called_once_with(["aiff", "wav", "mp3", "m4a", "caf"])
        panel.beginSheetModalForWindow_completionHandler_.assert_called_once()

        args = panel.beginSheetModalForWindow_completionHandler_.call_args[0]
        self.assertIs(args[0], self.controller._window)
        args[1](1)
        self.controller._handle_custom_sound_panel_result.assert_called_once_with(1, panel, True)


class TestSoundPopupActions(unittest.TestCase):
    def setUp(self):
        self.controller = SettingsWindowController.alloc().init()
        self.controller._prefs = MagicMock()
        self.controller._prefs.start_volume = 0.4
        self.controller._prefs.stop_volume = 0.6

    def test_start_sound_changed_schedules_custom_panel_after_menu_closes(self):
        sender = MagicMock()
        sender.titleOfSelectedItem.return_value = "Custom..."

        with patch("vvrite.settings.t", return_value="Custom..."), patch.object(
            self.controller, "performSelector_withObject_afterDelay_"
        ) as mock_schedule:
            self.controller.startSoundChanged_(sender)

        mock_schedule.assert_called_once_with("openStartCustomSoundPanel:", None, 0.0)

    def test_stop_sound_changed_schedules_custom_panel_after_menu_closes(self):
        sender = MagicMock()
        sender.titleOfSelectedItem.return_value = "Custom..."

        with patch("vvrite.settings.t", return_value="Custom..."), patch.object(
            self.controller, "performSelector_withObject_afterDelay_"
        ) as mock_schedule:
            self.controller.stopSoundChanged_(sender)

        mock_schedule.assert_called_once_with("openStopCustomSoundPanel:", None, 0.0)


class TestMicrophoneDeviceRefresh(unittest.TestCase):
    def setUp(self):
        self.controller = SettingsWindowController.alloc().init()
        self.controller._prefs = MagicMock()
        self.controller._prefs.mic_device = None
        self.controller._mic_popup = MagicMock()
        self.controller._mic_device_ids = [None]
        self.controller._mic_device_signature = ()

    @patch("vvrite.settings.resolve_input_device", return_value=None)
    @patch("vvrite.settings.get_default_input_device", return_value=None)
    @patch("vvrite.settings.list_input_devices")
    def test_populate_mics_can_refresh_portaudio_devices(
        self, mock_list_input_devices, mock_get_default, mock_resolve
    ):
        mock_list_input_devices.return_value = []

        self.controller._populate_mics(refresh=True)

        mock_list_input_devices.assert_called_once_with(refresh=True)

    @patch("vvrite.settings.list_input_devices")
    def test_poll_permissions_repopulates_mics_without_portaudio_refresh(
        self, mock_list_input_devices
    ):
        device = AudioInputDevice(
            device_id="Core Audio::DJI Mic Mini",
            name="DJI Mic Mini",
            display_name="DJI Mic Mini",
            index=8,
            hostapi_name="Core Audio",
            default_samplerate=48000,
        )
        mock_list_input_devices.return_value = [device]
        self.controller._update_permissions = MagicMock()
        self.controller._populate_mics = MagicMock()

        self.controller.pollPermissions_(MagicMock())

        mock_list_input_devices.assert_called_once_with(refresh=False)
        self.controller._populate_mics.assert_called_once_with(devices=[device])

    def test_show_window_refreshes_portaudio_device_list(self):
        self.controller._populate_mics = MagicMock()
        self.controller._populate_sounds = MagicMock()
        self.controller._window = MagicMock()

        with patch("vvrite.settings.NSApp"), patch("vvrite.settings.NSTimer"):
            self.controller.showWindow_(None)

        self.controller._populate_mics.assert_called_once_with(refresh=True)

    @patch("vvrite.settings.NSApp")
    @patch("vvrite.settings.list_input_devices")
    def test_poll_permissions_does_not_scan_audio_devices_while_recording(
        self, mock_list_input_devices, mock_app
    ):
        mock_app.delegate.return_value = SimpleNamespace(_recording=True)
        self.controller._update_permissions = MagicMock()
        self.controller._populate_mics = MagicMock()

        self.controller.pollPermissions_(MagicMock())

        mock_list_input_devices.assert_not_called()
        self.controller._populate_mics.assert_not_called()


class TestAsrModelSettingsActions(unittest.TestCase):
    def setUp(self):
        self.controller = SettingsWindowController.alloc().init()
        self.controller._prefs = MagicMock()
        self.controller._output_mode_popup = MagicMock()
        self.controller._model_downloading = False
        self.controller._download_progress_bar = None
        self.controller._download_progress_label = None
        self.translation_item = MagicMock()
        self.controller._output_mode_popup.itemAtIndex_.return_value = self.translation_item
        self.is_cached_patcher = patch(
            "vvrite.settings.transcriber.is_model_cached", return_value=False
        )
        self.is_cached_patcher.start()
        self.addCleanup(self.is_cached_patcher.stop)

    @patch("vvrite.settings.threading.Thread")
    def test_asr_model_changed_updates_pref_resets_translation_and_prepares_model(
        self, mock_thread
    ):
        self.controller._prefs.asr_model_key = "whisper_large_v3"
        self.controller._prefs.output_mode = "translate_to_english"
        sender = MagicMock()
        from vvrite.asr_models import ASR_MODELS

        sender.indexOfSelectedItem.return_value = list(ASR_MODELS).index(
            "whisper_large_v3_turbo_4bit"
        )

        self.controller.asrModelChanged_(sender)

        self.assertEqual(
            self.controller._prefs.asr_model_key,
            "whisper_large_v3_turbo_4bit",
        )
        self.assertEqual(self.controller._prefs.output_mode, "transcribe")
        self.controller._output_mode_popup.selectItemAtIndex_.assert_called_once_with(0)
        self.translation_item.setEnabled_.assert_called_once_with(False)
        self.assertTrue(self.controller._model_downloading)
        mock_thread.assert_called_once()
        self.assertEqual(
            mock_thread.call_args.kwargs["target"],
            self.controller._prepare_selected_model,
        )
        self.assertEqual(
            mock_thread.call_args.kwargs["args"],
            ("whisper_large_v3_turbo_4bit",),
        )
        self.assertTrue(mock_thread.call_args.kwargs["daemon"])
        mock_thread.return_value.start.assert_called_once_with()

    @patch("vvrite.settings.transcriber.prepare_model")
    def test_prepare_selected_model_downloads_missing_model_and_refreshes_state(
        self, mock_prepare_model
    ):
        self.controller.performSelectorOnMainThread_withObject_waitUntilDone_ = MagicMock()

        self.controller._prepare_selected_model("qwen3_asr_1_7b_8bit")

        mock_prepare_model.assert_called_once()
        self.assertEqual(
            mock_prepare_model.call_args.args[0], "qwen3_asr_1_7b_8bit"
        )
        self.assertIn("progress_callback", mock_prepare_model.call_args.kwargs)
        self.controller.performSelectorOnMainThread_withObject_waitUntilDone_.assert_any_call(
            "modelDownloadStateChanged:", None, False
        )

    @patch("vvrite.settings.transcriber.prepare_model")
    def test_prepare_selected_model_loads_cached_model(self, mock_prepare_model):
        self.controller.performSelectorOnMainThread_withObject_waitUntilDone_ = MagicMock()

        self.controller._prepare_selected_model("whisper_small_4bit")

        mock_prepare_model.assert_called_once()
        self.assertEqual(mock_prepare_model.call_args.args[0], "whisper_small_4bit")
        self.controller.performSelectorOnMainThread_withObject_waitUntilDone_.assert_any_call(
            "modelDownloadStateChanged:", None, False
        )

    def test_output_mode_changed_rejects_unsupported_translation(self):
        self.controller._prefs.asr_model_key = "qwen3_asr_1_7b_8bit"
        self.controller._prefs.output_mode = "transcribe"
        sender = MagicMock()
        sender.indexOfSelectedItem.return_value = 1

        self.controller.outputModeChanged_(sender)

        self.assertEqual(self.controller._prefs.output_mode, "transcribe")
        sender.selectItemAtIndex_.assert_called_once_with(0)
        self.translation_item.setEnabled_.assert_called_once_with(False)

    def test_output_mode_changed_accepts_small_whisper_translation(self):
        self.controller._prefs.asr_model_key = "whisper_small_4bit"
        self.controller._prefs.output_mode = "transcribe"
        sender = MagicMock()
        sender.indexOfSelectedItem.return_value = 1

        self.controller.outputModeChanged_(sender)

        self.assertEqual(self.controller._prefs.output_mode, "translate_to_english")
        sender.selectItemAtIndex_.assert_not_called()
        self.translation_item.setEnabled_.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
