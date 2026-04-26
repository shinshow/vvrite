"""Tests for onboarding download progress cleanup."""

import unittest
from unittest.mock import MagicMock

from vvrite.onboarding import OnboardingWindowController


class TestOnboardingProgress(unittest.TestCase):
    def _controller(self):
        controller = OnboardingWindowController.__new__(OnboardingWindowController)
        controller._status_bar = MagicMock()
        controller._progress_bar = MagicMock()
        controller._progress_label = MagicMock()
        controller._error_label = MagicMock()
        controller._retry_btn = MagicMock()
        controller._model_popup = None
        controller._load_retries = 0
        controller._update_buttons = MagicMock()
        return controller

    def test_model_load_complete_clears_menu_bar_download_progress(self):
        controller = self._controller()

        controller.modelLoadComplete_(None)

        controller._status_bar.setDownloadProgress_.assert_called_once_with(-1)

    def test_model_load_failure_clears_menu_bar_download_progress(self):
        controller = self._controller()

        controller.modelLoadFailed_("load failed")

        controller._status_bar.setDownloadProgress_.assert_called_once_with(-1)


if __name__ == "__main__":
    unittest.main()
