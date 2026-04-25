"""Tests for ASR transcriber router."""

import unittest
from unittest.mock import MagicMock, patch


class _Prefs:
    asr_model_key = "qwen3_asr_1_7b_8bit"


class TestTranscriberRouter(unittest.TestCase):
    def test_importing_transcriber_does_not_load_qwen_backend(self):
        import vvrite.transcriber as transcriber

        self.assertFalse(transcriber.is_model_loaded())

    @patch("vvrite.transcriber._qwen_backend")
    def test_get_model_size_routes_to_qwen_backend(self, mock_qwen_backend):
        backend = MagicMock()
        backend.get_size.return_value = 1_200_000_000
        mock_qwen_backend.return_value = backend

        from vvrite.transcriber import get_model_size

        size = get_model_size("qwen3_asr_1_7b_8bit")

        self.assertEqual(size, 1_200_000_000)
        backend.get_size.assert_called_once_with("mlx-community/Qwen3-ASR-1.7B-8bit")

    @patch("vvrite.transcriber._qwen_backend")
    def test_download_model_routes_to_qwen_backend(self, mock_qwen_backend):
        backend = MagicMock()
        backend.download.return_value = "/fake/path"
        mock_qwen_backend.return_value = backend

        from vvrite.transcriber import download_model

        path = download_model("qwen3_asr_1_7b_8bit")

        self.assertEqual(path, "/fake/path")
        backend.download.assert_called_once_with("mlx-community/Qwen3-ASR-1.7B-8bit")

    @patch("vvrite.transcriber._qwen_backend")
    def test_load_from_local_routes_to_selected_backend(self, mock_qwen_backend):
        backend = MagicMock()
        mock_qwen_backend.return_value = backend

        from vvrite import transcriber

        transcriber.load_from_local("/tmp/model", _Prefs())

        backend.load_from_local.assert_called_once_with("/tmp/model")
        self.assertTrue(transcriber.is_model_loaded())

    @patch("vvrite.transcriber._qwen_backend")
    def test_unload_releases_backend(self, mock_qwen_backend):
        backend = MagicMock()
        mock_qwen_backend.return_value = backend

        from vvrite import transcriber

        transcriber.load_from_local("/tmp/model", _Prefs())
        transcriber.unload()

        backend.unload.assert_called_once_with()
        self.assertFalse(transcriber.is_model_loaded())

    @patch("vvrite.transcriber._qwen_backend")
    def test_transcribe_routes_to_qwen_backend(self, mock_qwen_backend):
        backend = MagicMock()
        backend.transcribe.return_value = "hello"
        mock_qwen_backend.return_value = backend

        from vvrite.transcriber import transcribe

        result = transcribe("/tmp/audio.wav", _Prefs())

        self.assertEqual(result, "hello")
        backend.transcribe.assert_called_once()


if __name__ == "__main__":
    unittest.main()
