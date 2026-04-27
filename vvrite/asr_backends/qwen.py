"""Qwen3-ASR backend using mlx-audio."""

import concurrent.futures
import gc
import os
import sys
import tempfile
import threading

import numpy as np
import soundfile as sf
from huggingface_hub import model_info, snapshot_download
from tqdm.auto import tqdm

from vvrite import audio_utils, model_store
from vvrite.asr_language import resolve_asr_language
from vvrite.locales import ASR_LANGUAGE_MAP
from vvrite.preferences import SAMPLE_RATE
from vvrite.asr_prompts import transcription_prompt

_MODEL_KEY = "qwen3_asr_1_7b_8bit"
_model = None
_warmed_up = False
_worker_thread_id = None


class _ProgressTqdm(tqdm):
    """Aggregate Hugging Face per-file tqdm updates into one app callback."""

    _callback = None
    _total = 0
    _downloaded = 0
    _progress_state_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("disable", True)
        kwargs.setdefault("leave", False)
        super().__init__(*args, **kwargs)

    @classmethod
    def configure(cls, callback, total: int):
        with cls._progress_state_lock:
            cls._callback = callback
            cls._total = max(0, int(total or 0))
            cls._downloaded = 0

    @classmethod
    def clear(cls):
        with cls._progress_state_lock:
            cls._callback = None
            cls._total = 0
            cls._downloaded = 0

    def update(self, n=1):
        amount = int(n or 0)
        if amount <= 0:
            return
        super().update(amount)
        with type(self)._progress_state_lock:
            type(self)._downloaded += amount
            callback = type(self)._callback
            downloaded = type(self)._downloaded
            total = type(self)._total
        if callback is not None:
            callback(downloaded, total)


def _worker_initializer():
    global _worker_thread_id
    _worker_thread_id = threading.get_ident()


_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="vvrite-qwen-mlx",
    initializer=_worker_initializer,
)


def _run_on_worker(func, *args, **kwargs):
    if threading.get_ident() == _worker_thread_id:
        return func(*args, **kwargs)
    return _executor.submit(func, *args, **kwargs).result()


def is_loaded() -> bool:
    return _model is not None


def _unload_impl():
    global _model, _warmed_up
    _model = None
    _warmed_up = False
    _clear_mlx_cache()


def unload():
    _run_on_worker(_unload_impl)


def _clear_mlx_cache():
    gc.collect()
    mx = sys.modules.get("mlx.core")
    if mx is None:
        return
    try:
        clear_cache = getattr(mx, "clear_cache", None)
        if clear_cache is not None:
            clear_cache()
        metal = getattr(mx, "metal", None)
        if metal is not None:
            metal.clear_cache()
    except Exception:
        pass


def _model_key(model) -> str:
    return getattr(model, "key", _MODEL_KEY)


def _model_id(model) -> str:
    return getattr(model, "model_id", model)


def is_cached(model) -> bool:
    local_dir = model_store.model_dir(_model_key(model))
    try:
        snapshot_download(
            repo_id=_model_id(model),
            local_dir=local_dir,
            local_files_only=True,
            revision=getattr(model, "revision", None),
        )
        return True
    except Exception:
        return False


def get_size(model) -> int:
    try:
        info = model_info(
            _model_id(model),
            revision=getattr(model, "revision", None),
            files_metadata=True,
        )
        return sum(s.size for s in info.siblings if s.size)
    except Exception:
        return 0


def download(model, progress_callback=None) -> str:
    local_dir = model_store.model_dir(_model_key(model))
    total = get_size(model) if progress_callback is not None else 0
    if progress_callback is not None:
        progress_callback(0, total)
        _ProgressTqdm.configure(progress_callback, total)
    try:
        kwargs = {
            "repo_id": _model_id(model),
            "local_dir": local_dir,
            "revision": getattr(model, "revision", None),
        }
        if progress_callback is not None:
            kwargs["tqdm_class"] = _ProgressTqdm
        result = snapshot_download(**kwargs)
        if progress_callback is not None and total > 0:
            progress_callback(total, total)
        return result
    finally:
        _ProgressTqdm.clear()


def load_from_local(local_path: str):
    _run_on_worker(_load_from_local_impl, local_path)


def _load_from_local_impl(local_path: str):
    from mlx_audio.stt.utils import load_model

    global _model, _warmed_up
    _model = load_model(local_path)
    _warmed_up = False
    safe_warm_up()


def load(model):
    load_from_local(model_store.model_dir(_model_key(model)))


def _create_warmup_audio() -> str:
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    sf.write(path, np.zeros(SAMPLE_RATE // 2, dtype=np.float32), SAMPLE_RATE)
    return path


def warm_up():
    global _warmed_up
    if _model is None or _warmed_up:
        return

    warmup_path = _create_warmup_audio()
    try:
        _model.generate(warmup_path, max_tokens=1)
        _warmed_up = True
    finally:
        try:
            os.unlink(warmup_path)
        except OSError:
            pass


def safe_warm_up():
    try:
        warm_up()
    except Exception as e:
        print(f"Model warm-up skipped: {e}")


def transcribe(raw_wav_path: str, prefs) -> str:
    return _run_on_worker(_transcribe_impl, raw_wav_path, prefs)


def _transcribe_impl(raw_wav_path: str, prefs) -> str:
    if _model is None:
        raise RuntimeError("Qwen3-ASR model is not loaded")

    normalized_path = audio_utils.normalize(raw_wav_path)
    try:
        kwargs = {"max_tokens": prefs.max_tokens}
        custom_words = prefs.custom_words.strip()
        kwargs["system_prompt"] = transcription_prompt(custom_words)

        asr_lang = resolve_asr_language(prefs)
        if asr_lang != "auto":
            language_param = ASR_LANGUAGE_MAP.get(asr_lang)
            if language_param is None:
                print(
                    f"Unknown ASR language code: {asr_lang}, falling back to auto-detect"
                )
            else:
                kwargs["language"] = language_param

        result = _model.generate(normalized_path, **kwargs)
        return result.text.strip()
    finally:
        for path in (raw_wav_path, normalized_path):
            try:
                os.unlink(path)
            except OSError:
                pass
