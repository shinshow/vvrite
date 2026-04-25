"""Tests for ASR transcriber router."""

import unittest
from unittest.mock import MagicMock, patch


class _Prefs:
    asr_model_key = "qwen3_asr_1_7b_8bit"
    output_mode = "transcribe"


class _WhisperPrefs:
    asr_model_key = "whisper_large_v3"
    output_mode = "transcribe"


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

    @patch("vvrite.transcriber._whisper_backend")
    def test_download_model_routes_to_whisper_backend(self, mock_whisper_backend):
        backend = MagicMock()
        backend.download.return_value = "/models/ggml-large-v3.bin"
        mock_whisper_backend.return_value = backend

        from vvrite.transcriber import download_model

        path = download_model("whisper_large_v3")

        self.assertEqual(path, "/models/ggml-large-v3.bin")
        backend.download.assert_called_once()

    @patch("vvrite.transcriber._whisper_backend")
    def test_transcribe_routes_to_whisper_backend(self, mock_whisper_backend):
        backend = MagicMock()
        backend.transcribe.return_value = "translated text"
        mock_whisper_backend.return_value = backend

        from vvrite.transcriber import transcribe

        result = transcribe("/tmp/audio.wav", _WhisperPrefs())

        self.assertEqual(result, "translated text")
        backend.transcribe.assert_called_once()


class TestQwenBackend(unittest.TestCase):
    @patch("vvrite.asr_backends.qwen.model_store.model_dir", return_value="/tmp/qwen")
    @patch("vvrite.asr_backends.qwen.snapshot_download")
    def test_qwen_cache_check_does_not_require_model_load(
        self, mock_snapshot_download, mock_model_dir
    ):
        from vvrite.asr_backends import qwen

        self.assertTrue(qwen.is_cached("mlx-community/Qwen3-ASR-1.7B-8bit"))
        mock_snapshot_download.assert_called_once_with(
            repo_id="mlx-community/Qwen3-ASR-1.7B-8bit",
            local_dir="/tmp/qwen",
            local_files_only=True,
        )


if __name__ == "__main__":
    unittest.main()
