"""Tests for app launch sequencing."""

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, call, patch

from vvrite import main


class TestLaunchFlow(unittest.TestCase):
    @patch("vvrite.main.NSTimer")
    @patch("vvrite.main.transcriber.is_model_cached")
    @patch("vvrite.main.OverlayController")
    @patch("vvrite.main.StatusBarController")
    @patch("vvrite.locales.set_locale")
    @patch("vvrite.locales.resolve_system_locale", return_value="en")
    def test_launch_defers_model_cache_check_until_status_item_can_draw(
        self,
        _mock_resolve_locale,
        _mock_set_locale,
        mock_status_bar_controller,
        mock_overlay_controller,
        mock_is_model_cached,
        mock_timer,
    ):
        delegate = main.AppDelegate.__new__(main.AppDelegate)
        delegate._prefs = SimpleNamespace(
            ui_language=None,
            onboarding_completed=True,
            asr_model_key="whisper_large_v3_turbo_4bit",
        )
        delegate._status_bar = None
        delegate._overlay = None

        mock_status_bar_controller.alloc.return_value.initWithDelegate_.return_value = (
            MagicMock()
        )
        mock_overlay_controller.alloc.return_value.init.return_value = MagicMock()

        delegate.applicationDidFinishLaunching_(None)

        mock_is_model_cached.assert_not_called()
        mock_timer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_.assert_has_calls(
            [
                call(0.0, delegate, "finishLaunching:", None, False),
                call(1.0, delegate, "preloadSettings:", None, False),
            ]
        )

    @patch("vvrite.main.SettingsWindowController")
    def test_preload_settings_builds_window_before_menu_action(
        self, mock_settings_controller
    ):
        delegate = main.AppDelegate.__new__(main.AppDelegate)
        delegate._prefs = object()
        delegate._settings_wc = None
        controller = MagicMock()
        mock_settings_controller.alloc.return_value.initWithPreferences_.return_value = (
            controller
        )

        delegate.preloadSettings_(None)

        self.assertIs(delegate._settings_wc, controller)
        mock_settings_controller.alloc.return_value.initWithPreferences_.assert_called_once_with(
            delegate._prefs
        )

    @patch("vvrite.main.SettingsWindowController")
    def test_preload_settings_skips_while_onboarding_is_active(
        self, mock_settings_controller
    ):
        delegate = main.AppDelegate.__new__(main.AppDelegate)
        delegate._prefs = object()
        delegate._settings_wc = None
        delegate._onboarding_wc = object()

        delegate.preloadSettings_(None)

        self.assertIsNone(delegate._settings_wc)
        mock_settings_controller.alloc.assert_not_called()


if __name__ == "__main__":
    unittest.main()
