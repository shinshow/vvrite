"""Whisper backend using MLX Whisper models."""

from __future__ import annotations

import gc
from importlib import import_module
import os
import shutil
import sys
import threading

from huggingface_hub import model_info, snapshot_download
import numpy as np
import soundfile as sf
from tqdm.auto import tqdm

from vvrite import model_store
from vvrite.asr_language import resolve_asr_language
from vvrite.asr_models import OUTPUT_MODE_TRANSLATE_TO_ENGLISH
from vvrite.asr_prompts import transcription_prompt
from vvrite.preferences import SAMPLE_RATE

_loaded_model_key = None
_lock = threading.RLock()


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


def model_path(model) -> str:
    return model_store.model_dir(model.key)


def prepare_model_files(model):
    path = model_path(model)
    weights_path = os.path.join(path, "weights.safetensors")
    model_weights_path = os.path.join(path, "model.safetensors")
    if os.path.exists(weights_path) or not os.path.exists(model_weights_path):
        return
    try:
        os.link(model_weights_path, weights_path)
    except OSError:
        try:
            os.symlink(model_weights_path, weights_path)
        except OSError:
            shutil.copyfile(model_weights_path, weights_path)


def _mlx_whisper():
    return import_module("mlx_whisper")


def is_loaded() -> bool:
    with _lock:
        return _loaded_model_key is not None


def unload():
    global _loaded_model_key
    with _lock:
        _loaded_model_key = None
        _clear_model_holder_cache()
        _clear_mlx_cache()


def _clear_model_holder_cache():
    try:
        transcribe_func = getattr(_mlx_whisper(), "transcribe", None)
        holder = getattr(transcribe_func, "ModelHolder", None)
        if holder is not None:
            holder.model = None
            holder.model_path = None
    except Exception:
        pass


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


def is_cached(model) -> bool:
    try:
        snapshot_download(
            repo_id=model.model_id,
            local_dir=model_path(model),
            local_files_only=True,
            revision=model.revision,
        )
        prepare_model_files(model)
        return True
    except Exception:
        return False


def get_size(model) -> int:
    return _remote_size(model)


def _remote_size(model) -> int:
    try:
        info = model_info(
            model.model_id,
            revision=model.revision,
            files_metadata=True,
        )
        return sum(s.size for s in info.siblings if s.size)
    except Exception:
        return 0


def download(model, progress_callback=None) -> str:
    total = _remote_size(model)
    if progress_callback is not None:
        progress_callback(0, total)
        _ProgressTqdm.configure(progress_callback, total)
    try:
        kwargs = {
            "repo_id": model.model_id,
            "local_dir": model_path(model),
            "revision": model.revision,
        }
        if progress_callback is not None:
            kwargs["tqdm_class"] = _ProgressTqdm
        result = snapshot_download(**kwargs)
        prepare_model_files(model)
        if progress_callback is not None and total > 0:
            progress_callback(total, total)
        return result
    finally:
        _ProgressTqdm.clear()


def load(model):
    global _loaded_model_key
    with _lock:
        if _loaded_model_key == model.key:
            return
        prepare_model_files(model)
        _warm_up(model)
        _loaded_model_key = model.key


def _warm_up(model):
    samples = np.zeros(SAMPLE_RATE // 2, dtype=np.float32)
    _mlx_whisper().transcribe(
        samples,
        path_or_hf_repo=model_path(model),
        verbose=None,
        temperature=0.0,
        condition_on_previous_text=False,
        fp16=True,
    )


def _read_audio_samples(raw_wav_path: str) -> np.ndarray:
    samples, sample_rate = sf.read(raw_wav_path, dtype="float32", always_2d=False)
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim > 1:
        samples = np.mean(samples, axis=1, dtype=np.float32)
    if sample_rate == SAMPLE_RATE:
        return samples
    return _resample(samples, sample_rate, SAMPLE_RATE)


def _resample(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    try:
        from scipy.signal import resample_poly

        gcd = np.gcd(source_rate, target_rate)
        return resample_poly(samples, target_rate // gcd, source_rate // gcd).astype(
            np.float32,
            copy=False,
        )
    except Exception:
        duration = len(samples) / float(source_rate)
        if duration <= 0:
            return np.array([], dtype=np.float32)
        target_length = max(1, int(round(duration * target_rate)))
        source_x = np.linspace(0.0, duration, num=len(samples), endpoint=False)
        target_x = np.linspace(0.0, duration, num=target_length, endpoint=False)
        return np.interp(target_x, source_x, samples).astype(np.float32)


def _language_code(prefs) -> str | None:
    asr_language = resolve_asr_language(prefs)
    if asr_language == "auto":
        return None
    if asr_language in ("zh-Hans", "zh-Hant"):
        return "zh"
    return str(asr_language)


def _transcribe_kwargs(model, prefs):
    kwargs = {
        "path_or_hf_repo": model_path(model),
        "verbose": None,
        "temperature": 0.0,
        "condition_on_previous_text": False,
        "without_timestamps": True,
        "fp16": True,
        "task": (
            "translate"
            if prefs.output_mode == OUTPUT_MODE_TRANSLATE_TO_ENGLISH
            else "transcribe"
        ),
    }
    language = _language_code(prefs)
    if language is not None:
        kwargs["language"] = language
    custom_words = getattr(prefs, "custom_words", "").strip()
    if prefs.output_mode == OUTPUT_MODE_TRANSLATE_TO_ENGLISH:
        if custom_words:
            kwargs["initial_prompt"] = custom_words
    else:
        kwargs["initial_prompt"] = transcription_prompt(custom_words)
    return kwargs


def transcribe(raw_wav_path: str, model, prefs) -> str:
    with _lock:
        if _loaded_model_key != model.key:
            load(model)
        samples = _read_audio_samples(raw_wav_path)
        try:
            result = _mlx_whisper().transcribe(
                samples,
                **_transcribe_kwargs(model, prefs),
            )
            return str(result.get("text", "")).strip()
        finally:
            try:
                os.unlink(raw_wav_path)
            except OSError:
                pass
