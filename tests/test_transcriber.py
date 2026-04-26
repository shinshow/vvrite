"""Tests for ASR transcriber router."""

import unittest
import sys
import threading
import types
from unittest.mock import MagicMock, patch


class _Prefs:
    asr_model_key = "qwen3_asr_1_7b_8bit"
    output_mode = "transcribe"
    max_tokens = 256
    custom_words = ""
    asr_language = "auto"


class _WhisperPrefs:
    asr_model_key = "whisper_large_v3_turbo_4bit"
    output_mode = "transcribe"


class _WhisperMlxPrefs:
    asr_model_key = "whisper_small_4bit"
    output_mode = "transcribe"
    custom_words = ""
    asr_language = "auto"


class TestTranscriberRouter(unittest.TestCase):
    def setUp(self):
        from vvrite import transcriber

        transcriber._loaded_model_key = None

    def tearDown(self):
        from vvrite import transcriber

        transcriber._loaded_model_key = None

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
        backend.get_size.assert_called_once()
        self.assertEqual(backend.get_size.call_args.args[0].key, "qwen3_asr_1_7b_8bit")

    @patch("vvrite.transcriber._qwen_backend")
    def test_download_model_routes_to_qwen_backend(self, mock_qwen_backend):
        backend = MagicMock()
        backend.download.return_value = "/fake/path"
        mock_qwen_backend.return_value = backend

        from vvrite.transcriber import download_model

        path = download_model("qwen3_asr_1_7b_8bit")

        self.assertEqual(path, "/fake/path")
        backend.download.assert_called_once()
        self.assertEqual(backend.download.call_args.args[0].key, "qwen3_asr_1_7b_8bit")
        self.assertIsNone(backend.download.call_args.kwargs["progress_callback"])

    @patch("vvrite.transcriber._qwen_backend")
    def test_load_from_local_routes_to_selected_backend(self, mock_qwen_backend):
        backend = MagicMock()
        mock_qwen_backend.return_value = backend

        from vvrite import transcriber

        transcriber.load_from_local("/tmp/model", _Prefs())

        backend.load_from_local.assert_called_once_with("/tmp/model")
        self.assertTrue(transcriber.is_model_loaded())

    @patch("vvrite.transcriber._whisper_mlx_backend")
    def test_load_from_local_initializes_mlx_whisper_backend(self, mock_whisper_backend):
        backend = MagicMock()
        backend.is_loaded.return_value = True
        mock_whisper_backend.return_value = backend

        from vvrite import transcriber

        transcriber.load_from_local("/tmp/whisper-small", _WhisperMlxPrefs())

        backend.load.assert_called_once()
        self.assertEqual(backend.load.call_args.args[0].key, "whisper_small_4bit")
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

    @patch("vvrite.transcriber._whisper_mlx_backend")
    def test_get_model_size_routes_to_mlx_whisper_backend(self, mock_whisper_backend):
        backend = MagicMock()
        backend.get_size.return_value = 139_000_000
        mock_whisper_backend.return_value = backend

        from vvrite.transcriber import get_model_size

        size = get_model_size("whisper_small_4bit")

        self.assertEqual(size, 139_000_000)
        backend.get_size.assert_called_once()

    @patch("vvrite.transcriber._whisper_mlx_backend")
    def test_download_model_routes_to_whisper_backend(self, mock_whisper_backend):
        backend = MagicMock()
        backend.download.return_value = "/models/whisper-small-4bit"
        mock_whisper_backend.return_value = backend

        from vvrite.transcriber import download_model

        path = download_model("whisper_small_4bit")

        self.assertEqual(path, "/models/whisper-small-4bit")
        backend.download.assert_called_once()

    @patch("vvrite.transcriber._whisper_mlx_backend")
    def test_download_model_passes_progress_callback_to_backend(
        self, mock_whisper_backend
    ):
        backend = MagicMock()
        backend.download.return_value = "/models/whisper-small-4bit"
        mock_whisper_backend.return_value = backend

        from vvrite.transcriber import download_model

        callback = MagicMock()
        download_model("whisper_small_4bit", progress_callback=callback)

        backend.download.assert_called_once()
        self.assertIs(backend.download.call_args.kwargs["progress_callback"], callback)

    @patch("vvrite.transcriber._whisper_mlx_backend")
    def test_transcribe_routes_to_whisper_backend(self, mock_whisper_backend):
        backend = MagicMock()
        backend.is_cached.return_value = True
        backend.is_loaded.return_value = True
        backend.transcribe.return_value = "translated text"
        mock_whisper_backend.return_value = backend

        from vvrite.transcriber import transcribe

        result = transcribe("/tmp/audio.wav", _WhisperPrefs())

        self.assertEqual(result, "translated text")
        backend.transcribe.assert_called_once()

    @patch("vvrite.transcriber._whisper_mlx_backend")
    def test_load_initializes_whisper_backend(self, mock_whisper_backend):
        backend = MagicMock()
        backend.is_cached.return_value = True
        mock_whisper_backend.return_value = backend

        from vvrite import transcriber

        transcriber.load(_WhisperPrefs())

        backend.load.assert_called_once()
        self.assertEqual(
            backend.load.call_args.args[0].key,
            "whisper_large_v3_turbo_4bit",
        )
        self.assertTrue(transcriber.is_model_loaded())

    @patch("vvrite.transcriber._whisper_mlx_backend")
    @patch("vvrite.transcriber._qwen_backend")
    def test_transcribe_switches_to_selected_qwen_before_routing(
        self, mock_qwen_backend, mock_whisper_backend
    ):
        qwen_backend = MagicMock()
        qwen_backend.is_cached.return_value = True
        qwen_backend.transcribe.return_value = "hello"
        mock_qwen_backend.return_value = qwen_backend
        whisper_backend = MagicMock()
        mock_whisper_backend.return_value = whisper_backend

        from vvrite import transcriber

        transcriber._loaded_model_key = "whisper_large_v3_turbo_4bit"
        result = transcriber.transcribe("/tmp/audio.wav", _Prefs())

        self.assertEqual(result, "hello")
        whisper_backend.unload.assert_called_once_with()
        qwen_backend.load.assert_called_once()
        self.assertEqual(qwen_backend.load.call_args.args[0].key, "qwen3_asr_1_7b_8bit")
        qwen_backend.transcribe.assert_called_once()

    @patch("vvrite.transcriber._whisper_mlx_backend")
    @patch("vvrite.transcriber._qwen_backend")
    def test_prepare_model_downloads_missing_selected_model_before_loading(
        self, mock_qwen_backend, mock_whisper_backend
    ):
        qwen_backend = MagicMock()
        qwen_backend.is_cached.return_value = False
        qwen_backend.download.return_value = "/models/qwen"
        mock_qwen_backend.return_value = qwen_backend
        whisper_backend = MagicMock()
        mock_whisper_backend.return_value = whisper_backend

        from vvrite import transcriber

        transcriber._loaded_model_key = "whisper_large_v3_turbo_4bit"
        callback = MagicMock()
        transcriber.prepare_model(
            "qwen3_asr_1_7b_8bit",
            progress_callback=callback,
        )

        qwen_backend.download.assert_called_once()
        self.assertEqual(
            qwen_backend.download.call_args.args[0].key,
            "qwen3_asr_1_7b_8bit",
        )
        self.assertIs(qwen_backend.download.call_args.kwargs["progress_callback"], callback)
        whisper_backend.unload.assert_called_once_with()
        qwen_backend.load.assert_called_once()
        self.assertEqual(qwen_backend.load.call_args.args[0].key, "qwen3_asr_1_7b_8bit")
        self.assertTrue(transcriber.is_model_loaded())

    @patch("vvrite.transcriber._whisper_mlx_backend")
    @patch("vvrite.transcriber._qwen_backend")
    def test_ensure_model_cached_downloads_without_loading_or_unloading_current_model(
        self, mock_qwen_backend, mock_whisper_backend
    ):
        qwen_backend = MagicMock()
        mock_qwen_backend.return_value = qwen_backend
        whisper_backend = MagicMock()
        whisper_backend.is_cached.return_value = False
        whisper_backend.download.return_value = "/models/whisper-small"
        mock_whisper_backend.return_value = whisper_backend

        from vvrite import transcriber

        transcriber._loaded_model_key = "qwen3_asr_1_7b_8bit"
        callback = MagicMock()
        transcriber.ensure_model_cached(
            "whisper_small_4bit",
            progress_callback=callback,
        )

        whisper_backend.download.assert_called_once()
        self.assertEqual(
            whisper_backend.download.call_args.args[0].key,
            "whisper_small_4bit",
        )
        qwen_backend.unload.assert_not_called()
        whisper_backend.load.assert_not_called()
        self.assertEqual(transcriber._loaded_model_key, "qwen3_asr_1_7b_8bit")


class TestQwenBackend(unittest.TestCase):
    @patch("vvrite.asr_backends.qwen._clear_mlx_cache")
    def test_qwen_unload_clears_mlx_runtime_cache(self, mock_clear_cache):
        from vvrite.asr_backends import qwen

        qwen.unload()

        mock_clear_cache.assert_called_once_with()

    @patch("vvrite.asr_backends.qwen.model_store.model_dir", return_value="/tmp/qwen")
    @patch("vvrite.asr_backends.qwen.model_info")
    def test_qwen_download_progress_aggregates_huggingface_tqdm_updates(
        self, mock_model_info, mock_model_dir
    ):
        from vvrite.asr_backends import qwen

        mock_model_info.return_value = types.SimpleNamespace(
            siblings=[
                types.SimpleNamespace(size=100),
                types.SimpleNamespace(size=300),
            ]
        )
        progress = []

        def fake_snapshot_download(**kwargs):
            if "tqdm_class" not in kwargs:
                return "/tmp/qwen"
            progress_bar = kwargs["tqdm_class"]()
            progress_bar.update(100)
            progress_bar.update(300)
            return "/tmp/qwen"

        with patch(
            "vvrite.asr_backends.qwen.snapshot_download",
            side_effect=fake_snapshot_download,
        ):
            from vvrite.asr_models import get_model

            qwen.download(
                get_model("qwen3_asr_1_7b_8bit"),
                progress_callback=lambda downloaded, total: progress.append(
                    (downloaded, total)
                ),
            )

        self.assertEqual(progress, [(0, 400), (100, 400), (400, 400), (400, 400)])

    @patch("vvrite.asr_backends.qwen.model_store.model_dir", return_value="/tmp/qwen")
    @patch("vvrite.asr_backends.qwen.snapshot_download")
    def test_qwen_cache_check_does_not_require_model_load(
        self, mock_snapshot_download, mock_model_dir
    ):
        from vvrite.asr_backends import qwen
        from vvrite.asr_models import get_model

        self.assertTrue(qwen.is_cached(get_model("qwen3_asr_1_7b_8bit")))
        mock_snapshot_download.assert_called_once_with(
            repo_id="mlx-community/Qwen3-ASR-1.7B-8bit",
            local_dir="/tmp/qwen",
            local_files_only=True,
        )

    @patch("vvrite.asr_backends.qwen.safe_warm_up")
    @patch("vvrite.asr_backends.qwen.model_store.model_dir", return_value="/tmp/qwen")
    def test_qwen_load_uses_app_managed_model_dir(
        self, mock_model_dir, mock_safe_warm_up
    ):
        from vvrite.asr_backends import qwen
        from vvrite.asr_models import get_model

        fake_load_model = MagicMock()
        fake_utils = types.ModuleType("mlx_audio.stt.utils")
        fake_utils.load_model = fake_load_model
        fake_stt = types.ModuleType("mlx_audio.stt")
        fake_audio = types.ModuleType("mlx_audio")

        with patch.dict(
            sys.modules,
            {
                "mlx_audio": fake_audio,
                "mlx_audio.stt": fake_stt,
                "mlx_audio.stt.utils": fake_utils,
            },
        ):
            qwen.load(get_model("qwen3_asr_1_7b_8bit"))

        fake_load_model.assert_called_once_with("/tmp/qwen")

    @patch("vvrite.asr_backends.qwen.os.unlink")
    @patch("vvrite.asr_backends.qwen.audio_utils.normalize", return_value="/tmp/normalized.wav")
    @patch("vvrite.asr_backends.qwen.safe_warm_up")
    @patch("vvrite.asr_backends.qwen.model_store.model_dir", return_value="/tmp/qwen")
    def test_qwen_load_and_transcribe_run_on_same_worker_thread(
        self, mock_model_dir, mock_safe_warm_up, mock_normalize, mock_unlink
    ):
        from vvrite.asr_backends import qwen
        from vvrite.asr_models import get_model

        thread_ids = []

        class _Result:
            text = "hello"

        class _Model:
            def generate(self, *_args, **_kwargs):
                thread_ids.append(threading.get_ident())
                return _Result()

        def fake_load_model(_path):
            thread_ids.append(threading.get_ident())
            return _Model()

        fake_utils = types.ModuleType("mlx_audio.stt.utils")
        fake_utils.load_model = fake_load_model
        fake_stt = types.ModuleType("mlx_audio.stt")
        fake_audio = types.ModuleType("mlx_audio")

        with patch.dict(
            sys.modules,
            {
                "mlx_audio": fake_audio,
                "mlx_audio.stt": fake_stt,
                "mlx_audio.stt.utils": fake_utils,
            },
        ):
            qwen.unload()
            loaded = threading.Event()
            release_load_thread = threading.Event()

            def load_and_wait():
                qwen.load(get_model("qwen3_asr_1_7b_8bit"))
                loaded.set()
                release_load_thread.wait(timeout=5)

            load_thread = threading.Thread(target=load_and_wait)
            load_thread.start()
            self.assertTrue(loaded.wait(timeout=5))

            result = []
            transcribe_thread = threading.Thread(
                target=lambda: result.append(qwen.transcribe("/tmp/audio.wav", _Prefs()))
            )
            transcribe_thread.start()
            transcribe_thread.join()
            release_load_thread.set()
            load_thread.join()

        self.assertEqual(result, ["hello"])

        self.assertEqual(len(thread_ids), 2)
        self.assertEqual(thread_ids[0], thread_ids[1])

    @patch("vvrite.asr_backends.qwen.os.unlink")
    @patch("vvrite.asr_backends.qwen.audio_utils.normalize", return_value="/tmp/normalized.wav")
    @patch("vvrite.asr_backends.qwen.resolve_asr_language", return_value="auto")
    def test_qwen_auto_language_lets_model_detect_language(
        self, mock_resolve_language, mock_normalize, mock_unlink
    ):
        from vvrite.asr_backends import qwen

        class _Result:
            text = "마이크 테스트"

        model = MagicMock()
        model.generate.return_value = _Result()
        qwen._model = model

        try:
            self.assertEqual(qwen._transcribe_impl("/tmp/audio.wav", _Prefs()), "마이크 테스트")
        finally:
            qwen._model = None

        mock_resolve_language.assert_called_once()
        self.assertNotIn("language", model.generate.call_args.kwargs)
        self.assertIn("Do not translate", model.generate.call_args.kwargs["system_prompt"])

    @patch("vvrite.asr_backends.qwen.model_store.model_dir")
    @patch("vvrite.asr_backends.qwen.snapshot_download")
    def test_qwen_bf16_uses_model_specific_cache_directory(
        self, mock_snapshot_download, mock_model_dir
    ):
        from vvrite.asr_backends import qwen
        from vvrite.asr_models import get_model

        mock_model_dir.return_value = "/tmp/qwen-bf16"

        self.assertTrue(qwen.is_cached(get_model("qwen3_asr_1_7b_bf16")))

        mock_model_dir.assert_called_once_with("qwen3_asr_1_7b_bf16")
        mock_snapshot_download.assert_called_once_with(
            repo_id="mlx-community/Qwen3-ASR-1.7B-bf16",
            local_dir="/tmp/qwen-bf16",
            local_files_only=True,
        )


if __name__ == "__main__":
    unittest.main()
