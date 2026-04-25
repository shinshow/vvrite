"""ASR transcription router."""

from importlib import import_module

from vvrite.asr_models import BACKEND_QWEN_MLX, get_model
from vvrite.preferences import Preferences

_loaded_model_key = None


def _qwen_backend():
    return import_module("vvrite.asr_backends.qwen")


def _selected_model(prefs: Preferences | None = None):
    if prefs is None:
        prefs = Preferences()
    return get_model(prefs.asr_model_key)


def is_model_loaded() -> bool:
    return _loaded_model_key is not None


def is_model_cached(model_id_or_key: str) -> bool:
    model = get_model(model_id_or_key)
    if model.backend == BACKEND_QWEN_MLX:
        return _qwen_backend().is_cached(model.model_id)
    raise RuntimeError(f"Unsupported backend before Whisper task: {model.backend}")


def get_model_size(model_id_or_key: str) -> int:
    model = get_model(model_id_or_key)
    if model.backend == BACKEND_QWEN_MLX:
        return _qwen_backend().get_size(model.model_id)
    return 0


def download_model(model_id_or_key: str) -> str:
    model = get_model(model_id_or_key)
    if model.backend == BACKEND_QWEN_MLX:
        return _qwen_backend().download(model.model_id)
    raise RuntimeError(f"Unsupported backend before Whisper task: {model.backend}")


def load_from_local(local_path: str, prefs: Preferences = None):
    global _loaded_model_key
    model = _selected_model(prefs)
    if model.backend == BACKEND_QWEN_MLX:
        _qwen_backend().load_from_local(local_path)
        _loaded_model_key = model.key
        return
    raise RuntimeError(f"Unsupported backend before Whisper task: {model.backend}")


def load(prefs: Preferences = None):
    global _loaded_model_key
    if prefs is None:
        prefs = Preferences()
    model = _selected_model(prefs)
    print(f"Loading model: {model.display_name} ({model.model_id}) ...")
    if model.backend == BACKEND_QWEN_MLX:
        _qwen_backend().load(model.model_id)
        _loaded_model_key = model.key
        print("Model loaded.")
        return
    raise RuntimeError(f"Unsupported backend before Whisper task: {model.backend}")


def unload():
    global _loaded_model_key
    if _loaded_model_key is not None:
        model = get_model(_loaded_model_key)
        if model.backend == BACKEND_QWEN_MLX:
            _qwen_backend().unload()
    _loaded_model_key = None


def delete_model(model_key: str):
    from vvrite import model_store

    if _loaded_model_key == get_model(model_key).key:
        unload()
    model_store.delete_model_dir(get_model(model_key).key)


def transcribe(raw_wav_path: str, prefs: Preferences = None) -> str:
    if prefs is None:
        prefs = Preferences()
    model = _selected_model(prefs)
    if model.backend == BACKEND_QWEN_MLX:
        return _qwen_backend().transcribe(raw_wav_path, prefs)
    raise RuntimeError(f"Unsupported backend before Whisper task: {model.backend}")
