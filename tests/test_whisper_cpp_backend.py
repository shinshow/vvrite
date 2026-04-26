"""Tests for whisper.cpp backend."""

import os
import tempfile
import unittest
import ctypes
from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np

from vvrite.asr_models import OUTPUT_MODE_TRANSCRIBE, OUTPUT_MODE_TRANSLATE_TO_ENGLISH
from vvrite.asr_backends import whisper_cpp


class _Prefs:
    asr_language = "ko"
    output_mode = OUTPUT_MODE_TRANSCRIBE
    custom_words = "MLX, vvrite"


class TestWhisperCppBackend(unittest.TestCase):
    def tearDown(self):
        whisper_cpp.unload()

    def test_model_cache_path_uses_local_filename(self):
        model = MagicMock(key="whisper_large_v3", local_filename="ggml-large-v3.bin")
        with patch("vvrite.model_store.model_root", return_value="/tmp/models"):
            self.assertEqual(
                whisper_cpp.model_path(model),
                "/tmp/models/whisper_large_v3/ggml-large-v3.bin",
            )

    def test_is_cached_requires_file(self):
        model = MagicMock(key="whisper_large_v3", local_filename="ggml-large-v3.bin")
        with tempfile.TemporaryDirectory() as tmp:
            with patch("vvrite.model_store.model_root", return_value=tmp):
                self.assertFalse(whisper_cpp.is_cached(model))
                os.makedirs(os.path.join(tmp, "whisper_large_v3"), exist_ok=True)
                open(
                    os.path.join(tmp, "whisper_large_v3", "ggml-large-v3.bin"),
                    "wb",
                ).close()
                self.assertTrue(whisper_cpp.is_cached(model))

    def test_frozen_sidecar_dir_accepts_pyinstaller_dot_normalized_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            sidecar = os.path.join(tmp, "whisper__dot__cpp")
            os.makedirs(sidecar)
            with patch.object(whisper_cpp.sys, "frozen", True, create=True), patch.object(
                whisper_cpp.sys, "_MEIPASS", tmp, create=True
            ):
                self.assertEqual(whisper_cpp._sidecar_dir(), sidecar)

    @patch("vvrite.asr_backends.whisper_cpp.urllib.request.urlopen")
    def test_download_reports_byte_progress(self, mock_urlopen):
        model = MagicMock(
            key="whisper_large_v3",
            local_filename="ggml-large-v3.bin",
            download_url="https://example.com/model.bin",
        )
        response = MagicMock()
        response.headers = {"Content-Length": "6"}
        response.read.side_effect = [b"abc", b"def", b""]
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = response
        progress = []

        with tempfile.TemporaryDirectory() as tmp:
            with patch("vvrite.model_store.model_root", return_value=tmp):
                path = whisper_cpp.download(
                    model,
                    progress_callback=lambda downloaded, total: progress.append(
                        (downloaded, total)
                    ),
                )

            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"abcdef")

        self.assertEqual(progress, [(3, 6), (6, 6)])

    @patch("vvrite.asr_backends.whisper_cpp.subprocess.run")
    @patch("vvrite.asr_backends.whisper_cpp.binary_path", return_value="/app/whisper-cli")
    @patch(
        "vvrite.asr_backends.whisper_cpp.model_path",
        return_value="/models/ggml-large-v3.bin",
    )
    @patch("vvrite.audio_utils.normalize", return_value="/tmp/normalized.wav")
    def test_transcribe_invokes_whisper_cpp_with_language(
        self, mock_normalize, mock_model_path, mock_binary_path, mock_run
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout=" 안녕하세요 MLX", stderr="")
        model = MagicMock()
        result = whisper_cpp.transcribe("/tmp/raw.wav", model, _Prefs())
        self.assertEqual(result, "안녕하세요 MLX")
        args = mock_run.call_args.args[0]
        self.assertIn("-l", args)
        self.assertIn("ko", args)
        self.assertNotIn("--translate", args)
        self.assertIn("-bs", args)
        self.assertEqual(args[args.index("-bs") + 1], "1")
        self.assertIn("-bo", args)
        self.assertEqual(args[args.index("-bo") + 1], "1")
        self.assertIn("-nf", args)
        self.assertIn("-np", args)

    @patch("vvrite.asr_backends.whisper_cpp.subprocess.run")
    @patch("vvrite.asr_backends.whisper_cpp.binary_path", return_value="/app/whisper-cli")
    @patch(
        "vvrite.asr_backends.whisper_cpp.model_path",
        return_value="/models/ggml-large-v3.bin",
    )
    @patch("vvrite.audio_utils.normalize", return_value="/tmp/normalized.wav")
    def test_translate_mode_adds_translate_flag(
        self, mock_normalize, mock_model_path, mock_binary_path, mock_run
    ):
        prefs = _Prefs()
        prefs.output_mode = OUTPUT_MODE_TRANSLATE_TO_ENGLISH
        prefs.asr_language = "auto"
        mock_run.return_value = MagicMock(returncode=0, stdout="Hello", stderr="")
        whisper_cpp.transcribe("/tmp/raw.wav", MagicMock(), prefs)
        self.assertIn("--translate", mock_run.call_args.args[0])

    @patch("vvrite.asr_backends.whisper_cpp._load_library")
    @patch(
        "vvrite.asr_backends.whisper_cpp.model_path",
        return_value="/models/ggml-large-v3-turbo.bin",
    )
    def test_load_initializes_persistent_whisper_context(
        self, mock_model_path, mock_load_library
    ):
        fake_lib = MagicMock()
        fake_lib.whisper_context_default_params.return_value = (
            whisper_cpp._WhisperContextParams()
        )
        fake_lib.whisper_init_from_file_with_params.return_value = ctypes.c_void_p(7)
        mock_load_library.return_value = fake_lib

        model = MagicMock()
        whisper_cpp.load(model)

        self.assertTrue(whisper_cpp.is_loaded())
        fake_lib.whisper_init_from_file_with_params.assert_called_once()
        self.assertEqual(
            fake_lib.whisper_init_from_file_with_params.call_args.args[0],
            b"/models/ggml-large-v3-turbo.bin",
        )

    @patch("vvrite.asr_backends.whisper_cpp.os.unlink")
    @patch("vvrite.asr_backends.whisper_cpp.sf.read")
    @patch("vvrite.audio_utils.normalize", return_value="/tmp/normalized.wav")
    @patch("vvrite.asr_backends.whisper_cpp._load_library")
    @patch(
        "vvrite.asr_backends.whisper_cpp.model_path",
        return_value="/models/ggml-large-v3-turbo.bin",
    )
    def test_transcribe_uses_persistent_context_when_loaded(
        self, mock_model_path, mock_load_library, mock_normalize, mock_read, mock_unlink
    ):
        fake_lib = MagicMock()
        fake_lib.whisper_context_default_params.return_value = (
            whisper_cpp._WhisperContextParams()
        )
        fake_lib.whisper_init_from_file_with_params.return_value = ctypes.c_void_p(7)
        fake_lib.whisper_full_default_params.return_value = (
            whisper_cpp._WhisperFullParams()
        )
        fake_lib.whisper_full.return_value = 0
        fake_lib.whisper_full_n_segments.return_value = 1
        fake_lib.whisper_full_get_segment_text.return_value = b" hello"
        mock_load_library.return_value = fake_lib
        mock_read.return_value = (np.zeros(16000, dtype=np.float32), 16000)

        model = MagicMock()
        whisper_cpp.load(model)
        result = whisper_cpp.transcribe("/tmp/raw.wav", model, _Prefs())

        self.assertEqual(result, "hello")
        fake_lib.whisper_full.assert_called_once()
        params = fake_lib.whisper_full.call_args.args[1]
        self.assertEqual(params.greedy.best_of, 1)
        self.assertEqual(params.beam_search.beam_size, 1)
        self.assertEqual(params.temperature_inc, 0.0)
        self.assertTrue(params.single_segment)
        self.assertEqual(params.audio_ctx, 256)

    @patch("vvrite.asr_backends.whisper_cpp._lib")
    def test_make_full_params_scales_audio_context_with_input_length(self, mock_lib):
        mock_lib.whisper_full_default_params.side_effect = (
            lambda _strategy: whisper_cpp._WhisperFullParams()
        )

        short_params, _ = whisper_cpp._make_full_params(_Prefs(), 16000 * 2)
        long_params, _ = whisper_cpp._make_full_params(_Prefs(), 16000 * 30)

        self.assertEqual(short_params.audio_ctx, 256)
        self.assertEqual(long_params.audio_ctx, 1500)

    @patch("vvrite.asr_backends.whisper_cpp.sf.read")
    @patch("vvrite.audio_utils.normalize")
    def test_read_samples_avoids_ffmpeg_when_input_is_already_16khz_mono_wav(
        self, mock_normalize, mock_read
    ):
        samples = np.zeros(16000, dtype=np.float32)
        mock_read.return_value = (samples, 16000)

        result, cleanup_path = whisper_cpp._read_transcription_samples("/tmp/raw.wav")

        self.assertIs(cleanup_path, None)
        self.assertEqual(result.dtype, np.float32)
        mock_normalize.assert_not_called()

    @patch("vvrite.asr_backends.whisper_cpp.sf.read")
    @patch("vvrite.audio_utils.normalize")
    def test_read_samples_resamples_non_16khz_input_without_ffmpeg(
        self, mock_normalize, mock_read
    ):
        mock_read.return_value = (np.zeros(48000, dtype=np.float32), 48000)

        result, cleanup_path = whisper_cpp._read_transcription_samples("/tmp/raw.wav")

        self.assertIs(cleanup_path, None)
        self.assertEqual(result.shape, (16000,))
        self.assertEqual(result.dtype, np.float32)
        mock_normalize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
