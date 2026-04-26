"""Tests for MLX Whisper backend."""

import os
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from vvrite.asr_models import get_model
from vvrite.asr_backends import whisper_mlx


class _Prefs:
    output_mode = "transcribe"
    custom_words = ""
    asr_language = "auto"


class TestWhisperMlxBackend(unittest.TestCase):
    def tearDown(self):
        whisper_mlx.unload()

    @patch("vvrite.asr_backends.whisper_mlx.model_store.model_dir")
    def test_model_path_uses_app_managed_directory(self, mock_model_dir):
        mock_model_dir.return_value = "/tmp/models/whisper-small-4bit"
        model = get_model("whisper_small_4bit")

        self.assertEqual(
            whisper_mlx.model_path(model),
            "/tmp/models/whisper-small-4bit",
        )

    @patch("vvrite.asr_backends.whisper_mlx.model_store.model_dir")
    def test_prepare_model_files_aliases_model_safetensors_for_mlx_whisper(
        self, mock_model_dir
    ):
        with tempfile.TemporaryDirectory() as tmp:
            mock_model_dir.return_value = tmp
            source = os.path.join(tmp, "model.safetensors")
            target = os.path.join(tmp, "weights.safetensors")
            with open(source, "wb") as f:
                f.write(b"weights")

            whisper_mlx.prepare_model_files(get_model("whisper_small_4bit"))

            self.assertTrue(os.path.exists(target))
            with open(target, "rb") as f:
                self.assertEqual(f.read(), b"weights")

    @patch("vvrite.asr_backends.whisper_mlx._mlx_whisper")
    @patch("vvrite.asr_backends.whisper_mlx.model_store.model_dir")
    def test_load_prepares_model_files_before_warmup(
        self, mock_model_dir, mock_mlx_whisper
    ):
        with tempfile.TemporaryDirectory() as tmp:
            mock_model_dir.return_value = tmp
            with open(os.path.join(tmp, "model.safetensors"), "wb") as f:
                f.write(b"weights")
            mock_mlx_whisper.return_value.transcribe.return_value = {"text": ""}

            whisper_mlx.load(get_model("whisper_small_4bit"))

            self.assertTrue(os.path.exists(os.path.join(tmp, "weights.safetensors")))
            mock_mlx_whisper.return_value.transcribe.assert_called_once()

    @patch("vvrite.asr_backends.whisper_mlx.model_store.model_dir")
    @patch("vvrite.asr_backends.whisper_mlx.snapshot_download")
    def test_cache_check_uses_local_snapshot(self, mock_snapshot_download, mock_model_dir):
        mock_model_dir.return_value = "/tmp/models/whisper-small-4bit"
        model = get_model("whisper_small_4bit")

        self.assertTrue(whisper_mlx.is_cached(model))

        mock_snapshot_download.assert_called_once_with(
            repo_id="mlx-community/whisper-small-4bit",
            local_dir="/tmp/models/whisper-small-4bit",
            local_files_only=True,
        )

    @patch("vvrite.asr_backends.whisper_mlx.model_store.model_dir")
    @patch("vvrite.asr_backends.whisper_mlx.snapshot_download")
    @patch("vvrite.asr_backends.whisper_mlx.model_info")
    def test_download_uses_model_specific_directory(
        self, mock_model_info, mock_snapshot_download, mock_model_dir
    ):
        mock_model_dir.return_value = "/tmp/models/whisper-small-4bit"
        mock_snapshot_download.return_value = "/tmp/models/whisper-small-4bit"
        mock_model_info.return_value = types.SimpleNamespace(
            siblings=[
                types.SimpleNamespace(size=100),
                types.SimpleNamespace(size=50),
            ]
        )
        progress = MagicMock()

        path = whisper_mlx.download(get_model("whisper_small_4bit"), progress)

        self.assertEqual(path, "/tmp/models/whisper-small-4bit")
        mock_snapshot_download.assert_called_once_with(
            repo_id="mlx-community/whisper-small-4bit",
            local_dir="/tmp/models/whisper-small-4bit",
            tqdm_class=whisper_mlx._ProgressTqdm,
        )
        progress.assert_any_call(0, 150)
        progress.assert_any_call(150, 150)

    @patch("vvrite.asr_backends.whisper_mlx.model_store.model_dir")
    @patch("vvrite.asr_backends.whisper_mlx.model_info")
    def test_download_progress_aggregates_huggingface_tqdm_updates(
        self, mock_model_info, mock_model_dir
    ):
        mock_model_dir.return_value = "/tmp/models/whisper-small-4bit"
        mock_model_info.return_value = types.SimpleNamespace(
            siblings=[
                types.SimpleNamespace(size=100),
                types.SimpleNamespace(size=50),
            ]
        )
        progress = MagicMock()

        def fake_snapshot_download(**kwargs):
            bar = kwargs["tqdm_class"](total=100)
            bar.update(40)
            bar.update(60)
            second = kwargs["tqdm_class"](total=50)
            second.update(50)
            return "/tmp/models/whisper-small-4bit"

        with patch(
            "vvrite.asr_backends.whisper_mlx.snapshot_download",
            side_effect=fake_snapshot_download,
        ):
            whisper_mlx.download(get_model("whisper_small_4bit"), progress)

        self.assertIn(((40, 150),), progress.call_args_list)
        self.assertIn(((100, 150),), progress.call_args_list)
        self.assertIn(((150, 150),), progress.call_args_list)

    def test_progress_tqdm_is_compatible_with_locking_and_refresh(self):
        progress = MagicMock()
        lock = whisper_mlx._ProgressTqdm.get_lock()
        whisper_mlx._ProgressTqdm.set_lock(lock)
        whisper_mlx._ProgressTqdm.configure(progress, 10)
        try:
            with whisper_mlx._ProgressTqdm(total=10) as bar:
                bar.refresh()
                bar.update(3)
                bar.close()
        finally:
            whisper_mlx._ProgressTqdm.clear()

        progress.assert_called_with(3, 10)

    @patch("vvrite.asr_backends.whisper_mlx.resolve_asr_language", return_value="auto")
    @patch("vvrite.asr_backends.whisper_mlx._read_audio_samples")
    @patch("vvrite.asr_backends.whisper_mlx.model_path")
    def test_transcribe_auto_language_lets_model_detect_language(
        self, mock_model_path, mock_read_audio, mock_resolve_language
    ):
        fake_mlx_whisper = types.SimpleNamespace(transcribe=MagicMock())
        fake_mlx_whisper.transcribe.return_value = {"text": " hello "}
        mock_model_path.return_value = "/tmp/models/whisper-small-4bit"
        mock_read_audio.return_value = np.zeros(16000, dtype=np.float32)
        model = get_model("whisper_small_4bit")

        with patch.dict(sys.modules, {"mlx_whisper": fake_mlx_whisper}):
            result = whisper_mlx.transcribe("/tmp/raw.wav", model, _Prefs())

        self.assertEqual(result, "hello")
        self.assertEqual(fake_mlx_whisper.transcribe.call_count, 2)
        kwargs = fake_mlx_whisper.transcribe.call_args.kwargs
        self.assertEqual(kwargs["path_or_hf_repo"], "/tmp/models/whisper-small-4bit")
        self.assertEqual(kwargs["temperature"], 0.0)
        self.assertFalse(kwargs["condition_on_previous_text"])
        self.assertTrue(kwargs["without_timestamps"])
        self.assertEqual(kwargs["task"], "transcribe")
        self.assertNotIn("language", kwargs)
        self.assertIn("Do not translate", kwargs["initial_prompt"])
        mock_resolve_language.assert_called()

    def test_unload_clears_mlx_whisper_model_holder_cache(self):
        model_holder = types.SimpleNamespace(model=object(), model_path="/tmp/model")
        fake_transcribe = types.SimpleNamespace(ModelHolder=model_holder)
        fake_mlx_whisper = types.SimpleNamespace(transcribe=fake_transcribe)

        with patch.dict(sys.modules, {"mlx_whisper": fake_mlx_whisper}):
            whisper_mlx.unload()

        self.assertIsNone(model_holder.model)
        self.assertIsNone(model_holder.model_path)

    @patch("vvrite.asr_backends.whisper_mlx._read_audio_samples")
    @patch("vvrite.asr_backends.whisper_mlx.model_path")
    def test_transcribe_maps_language_and_custom_words(
        self, mock_model_path, mock_read_audio
    ):
        fake_mlx_whisper = types.SimpleNamespace(transcribe=MagicMock())
        fake_mlx_whisper.transcribe.return_value = {"text": "안녕하세요"}
        mock_model_path.return_value = "/tmp/models/whisper-small-4bit"
        mock_read_audio.return_value = np.zeros(16000, dtype=np.float32)

        class _KoreanPrefs:
            output_mode = "transcribe"
            custom_words = "vvrite, Qwen"
            asr_language = "ko"

        with patch.dict(sys.modules, {"mlx_whisper": fake_mlx_whisper}):
            whisper_mlx.transcribe(
                "/tmp/raw.wav", get_model("whisper_small_4bit"), _KoreanPrefs()
            )

        kwargs = fake_mlx_whisper.transcribe.call_args.kwargs
        self.assertEqual(kwargs["language"], "ko")
        self.assertIn("Do not translate", kwargs["initial_prompt"])
        self.assertIn("vvrite, Qwen", kwargs["initial_prompt"])

    @patch("vvrite.asr_backends.whisper_mlx.resolve_asr_language", return_value="auto")
    def test_transcribe_kwargs_omits_language_for_auto_detection(
        self, mock_resolve_language
    ):
        kwargs = whisper_mlx._transcribe_kwargs(get_model("whisper_small_4bit"), _Prefs())

        mock_resolve_language.assert_called_once()
        self.assertNotIn("language", kwargs)

    @patch("vvrite.asr_backends.whisper_mlx._read_audio_samples")
    @patch("vvrite.asr_backends.whisper_mlx.model_path")
    def test_transcribe_uses_translate_task_for_supported_models(
        self, mock_model_path, mock_read_audio
    ):
        fake_mlx_whisper = types.SimpleNamespace(transcribe=MagicMock())
        fake_mlx_whisper.transcribe.return_value = {"text": "hello"}
        mock_model_path.return_value = "/tmp/models/whisper-small-4bit"
        mock_read_audio.return_value = np.zeros(16000, dtype=np.float32)

        class _TranslatePrefs:
            output_mode = "translate_to_english"
            custom_words = ""
            asr_language = "auto"

        with patch.dict(sys.modules, {"mlx_whisper": fake_mlx_whisper}):
            whisper_mlx.transcribe(
                "/tmp/raw.wav", get_model("whisper_small_4bit"), _TranslatePrefs()
            )

        self.assertEqual(fake_mlx_whisper.transcribe.call_args.kwargs["task"], "translate")

    @patch("vvrite.asr_backends.whisper_mlx.sf.read")
    def test_read_audio_samples_avoids_ffmpeg_for_16khz_mono_wav(self, mock_read):
        samples = np.array([0.0, 0.25, -0.25], dtype=np.float32)
        mock_read.return_value = (samples, 16000)

        result = whisper_mlx._read_audio_samples("/tmp/raw.wav")

        np.testing.assert_array_equal(result, samples)

    @patch("vvrite.asr_backends.whisper_mlx.os.unlink")
    @patch("vvrite.asr_backends.whisper_mlx._read_audio_samples")
    @patch("vvrite.asr_backends.whisper_mlx.model_path")
    def test_transcribe_removes_raw_audio_after_use(
        self, mock_model_path, mock_read_audio, mock_unlink
    ):
        fake_mlx_whisper = types.SimpleNamespace(transcribe=MagicMock())
        fake_mlx_whisper.transcribe.return_value = {"text": "hello"}
        mock_model_path.return_value = "/tmp/models/whisper-small-4bit"
        mock_read_audio.return_value = np.zeros(16000, dtype=np.float32)

        with patch.dict(sys.modules, {"mlx_whisper": fake_mlx_whisper}):
            whisper_mlx.transcribe("/tmp/raw.wav", get_model("whisper_small_4bit"), _Prefs())

        mock_unlink.assert_called_once_with("/tmp/raw.wav")


if __name__ == "__main__":
    unittest.main()
