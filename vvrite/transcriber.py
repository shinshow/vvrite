"""ASR transcription router."""

from importlib import import_module
import os
import threading

from huggingface_hub import model_info

from vvrite.asr_models import (
    BACKEND_QWEN_MLX,
    BACKEND_WHISPER_CPP,
    BACKEND_WHISPER_MLX,
    get_model,
    is_output_mode_supported,
)
from vvrite.preferences import Preferences

_loaded_model_key = None
_model_lock = threading.RLock()


def _qwen_backend():
    return import_module("vvrite.asr_backends.qwen")


def _whisper_backend():
    return import_module("vvrite.asr_backends.whisper_cpp")


def _whisper_mlx_backend():
    return import_module("vvrite.asr_backends.whisper_mlx")


def _selected_model(prefs: Preferences | None = None):
    if prefs is None:
        prefs = Preferences()
    return get_model(prefs.asr_model_key)


def is_model_loaded() -> bool:
    with _model_lock:
        if _loaded_model_key is None:
            return False
        model = get_model(_loaded_model_key)
        if model.backend == BACKEND_QWEN_MLX:
            return _qwen_backend().is_loaded()
        if model.backend == BACKEND_WHISPER_CPP:
            return _whisper_backend().is_loaded()
        if model.backend == BACKEND_WHISPER_MLX:
            return _whisper_mlx_backend().is_loaded()
        return False


def _model_from(value=None):
    if value is None:
        return _selected_model()
    if isinstance(value, str):
        return get_model(value)
    return get_model(value.asr_model_key)


def _is_model_cached(model) -> bool:
    if model.backend == BACKEND_QWEN_MLX:
        return _qwen_backend().is_cached(model)
    if model.backend == BACKEND_WHISPER_CPP:
        return _whisper_backend().is_cached(model)
    if model.backend == BACKEND_WHISPER_MLX:
        return _whisper_mlx_backend().is_cached(model)
    raise RuntimeError(f"Unsupported backend before Whisper task: {model.backend}")


def _is_loaded_model_ready(model) -> bool:
    if _loaded_model_key != model.key:
        return False
    if model.backend == BACKEND_QWEN_MLX:
        return _qwen_backend().is_loaded()
    if model.backend == BACKEND_WHISPER_CPP:
        return _whisper_backend().is_loaded() and _whisper_backend().is_cached(model)
    if model.backend == BACKEND_WHISPER_MLX:
        return _whisper_mlx_backend().is_loaded() and _whisper_mlx_backend().is_cached(
            model
        )
    return False


def _unload_loaded_model():
    global _loaded_model_key
    if _loaded_model_key is not None:
        model = get_model(_loaded_model_key)
        if model.backend == BACKEND_QWEN_MLX:
            _qwen_backend().unload()
        elif model.backend == BACKEND_WHISPER_CPP:
            _whisper_backend().unload()
        elif model.backend == BACKEND_WHISPER_MLX:
            _whisper_mlx_backend().unload()
    _loaded_model_key = None


def _load_model(model):
    global _loaded_model_key
    print(f"Loading model: {model.display_name} ({model.model_id}) ...")
    if model.backend == BACKEND_QWEN_MLX:
        _qwen_backend().load(model)
        _loaded_model_key = model.key
        print("Model loaded.")
        return
    if model.backend == BACKEND_WHISPER_CPP:
        if not _whisper_backend().is_cached(model):
            raise RuntimeError(f"{model.display_name} is not downloaded")
        _whisper_backend().load(model)
        _loaded_model_key = model.key
        print("Model ready.")
        return
    if model.backend == BACKEND_WHISPER_MLX:
        if not _whisper_mlx_backend().is_cached(model):
            raise RuntimeError(f"{model.display_name} is not downloaded")
        _whisper_mlx_backend().load(model)
        _loaded_model_key = model.key
        print("Model ready.")
        return
    raise RuntimeError(f"Unsupported backend before Whisper task: {model.backend}")


def prepare_model(model_or_prefs=None, progress_callback=None):
    """Ensure the selected ASR model is downloaded and active."""
    with _model_lock:
        model = _model_from(model_or_prefs)
        if _is_loaded_model_ready(model):
            return model
        if not _is_model_cached(model):
            download_model(model.key, progress_callback=progress_callback)
        if _loaded_model_key is not None:
            _unload_loaded_model()
        _load_model(model)
        return model


def ensure_model_cached(model_or_prefs=None, progress_callback=None):
    """Ensure the selected ASR model is downloaded without loading it."""
    with _model_lock:
        model = _model_from(model_or_prefs)
        if not _is_model_cached(model):
            download_model(model.key, progress_callback=progress_callback)
        return model


def is_model_cached(model_id_or_key: str) -> bool:
    model = get_model(model_id_or_key)
    return _is_model_cached(model)


def get_model_size(model_id_or_key: str) -> int:
    model = get_model(model_id_or_key)
    if model.backend == BACKEND_QWEN_MLX:
        return _qwen_backend().get_size(model)
    if model.backend == BACKEND_WHISPER_CPP:
        return _whisper_backend().get_size(model)
    if model.backend == BACKEND_WHISPER_MLX:
        return _whisper_mlx_backend().get_size(model)
    return 0


def download_model(model_id_or_key: str, progress_callback=None) -> str:
    model = get_model(model_id_or_key)
    if model.backend == BACKEND_QWEN_MLX:
        return _qwen_backend().download(
            model,
            progress_callback=progress_callback,
        )
    if model.backend == BACKEND_WHISPER_CPP:
        return _whisper_backend().download(
            model,
            progress_callback=progress_callback,
        )
    if model.backend == BACKEND_WHISPER_MLX:
        return _whisper_mlx_backend().download(
            model,
            progress_callback=progress_callback,
        )
    raise RuntimeError(f"Unsupported backend before Whisper task: {model.backend}")


def latest_model_revision(model_id_or_key: str) -> str:
    model = get_model(model_id_or_key)
    info = model_info(model.model_id)
    return str(info.sha or "")


def load_from_local(local_path: str, prefs: Preferences = None):
    global _loaded_model_key
    with _model_lock:
        model = _selected_model(prefs)
        if _loaded_model_key is not None and _loaded_model_key != model.key:
            _unload_loaded_model()
        if model.backend == BACKEND_QWEN_MLX:
            _qwen_backend().load_from_local(local_path)
            _loaded_model_key = model.key
            return
        if model.backend == BACKEND_WHISPER_CPP:
            _loaded_model_key = model.key
            return
        if model.backend == BACKEND_WHISPER_MLX:
            _whisper_mlx_backend().load(model)
            _loaded_model_key = model.key
            return
        raise RuntimeError(f"Unsupported backend before Whisper task: {model.backend}")


def load(prefs: Preferences = None):
    if prefs is None:
        prefs = Preferences()
    with _model_lock:
        model = _selected_model(prefs)
        if _is_loaded_model_ready(model):
            return
        if _loaded_model_key is not None:
            _unload_loaded_model()
        _load_model(model)


def unload():
    with _model_lock:
        _unload_loaded_model()


def delete_model(model_key: str):
    from vvrite import model_store

    with _model_lock:
        if _loaded_model_key == get_model(model_key).key:
            _unload_loaded_model()
        model_store.delete_model_dir(get_model(model_key).key)


def transcribe(raw_wav_path: str, prefs: Preferences = None) -> str:
    if prefs is None:
        prefs = Preferences()
    with _model_lock:
        model = _selected_model(prefs)
        backend_will_cleanup = False
        try:
            if not is_output_mode_supported(model.key, prefs.output_mode):
                raise RuntimeError(
                    f"{model.display_name} does not support output mode {prefs.output_mode}"
                )
            prepare_model(prefs)
            backend_will_cleanup = True
        finally:
            if not backend_will_cleanup:
                try:
                    os.unlink(raw_wav_path)
                except OSError:
                    pass
        if model.backend == BACKEND_QWEN_MLX:
            return _qwen_backend().transcribe(raw_wav_path, prefs)
        if model.backend == BACKEND_WHISPER_CPP:
            return _whisper_backend().transcribe(raw_wav_path, model, prefs)
        if model.backend == BACKEND_WHISPER_MLX:
            return _whisper_mlx_backend().transcribe(raw_wav_path, model, prefs)
        raise RuntimeError(f"Unsupported backend before Whisper task: {model.backend}")
