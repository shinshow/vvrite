"""Whisper backend using a bundled whisper.cpp sidecar."""

from __future__ import annotations

import ctypes
import math
import os
import subprocess
import sys
import threading
import urllib.request

import numpy as np
import soundfile as sf

from vvrite import audio_utils, model_store
from vvrite.asr_models import OUTPUT_MODE_TRANSLATE_TO_ENGLISH

WHISPER_SAMPLING_GREEDY = 0
_lib = None
_ctx = None
_loaded_model_key = None
_lock = threading.RLock()


class _WhisperAhead(ctypes.Structure):
    _fields_ = [
        ("n_text_layer", ctypes.c_int),
        ("n_head", ctypes.c_int),
    ]


class _WhisperAheads(ctypes.Structure):
    _fields_ = [
        ("n_heads", ctypes.c_size_t),
        ("heads", ctypes.POINTER(_WhisperAhead)),
    ]


class _WhisperContextParams(ctypes.Structure):
    _fields_ = [
        ("use_gpu", ctypes.c_bool),
        ("flash_attn", ctypes.c_bool),
        ("gpu_device", ctypes.c_int),
        ("dtw_token_timestamps", ctypes.c_bool),
        ("dtw_aheads_preset", ctypes.c_int),
        ("dtw_n_top", ctypes.c_int),
        ("dtw_aheads", _WhisperAheads),
        ("dtw_mem_size", ctypes.c_size_t),
    ]


class _WhisperVadParams(ctypes.Structure):
    _fields_ = [
        ("threshold", ctypes.c_float),
        ("min_speech_duration_ms", ctypes.c_int),
        ("min_silence_duration_ms", ctypes.c_int),
        ("max_speech_duration_s", ctypes.c_float),
        ("speech_pad_ms", ctypes.c_int),
        ("samples_overlap", ctypes.c_float),
    ]


class _WhisperGreedyParams(ctypes.Structure):
    _fields_ = [("best_of", ctypes.c_int)]


class _WhisperBeamSearchParams(ctypes.Structure):
    _fields_ = [
        ("beam_size", ctypes.c_int),
        ("patience", ctypes.c_float),
    ]


class _WhisperFullParams(ctypes.Structure):
    _fields_ = [
        ("strategy", ctypes.c_int),
        ("n_threads", ctypes.c_int),
        ("n_max_text_ctx", ctypes.c_int),
        ("offset_ms", ctypes.c_int),
        ("duration_ms", ctypes.c_int),
        ("translate", ctypes.c_bool),
        ("no_context", ctypes.c_bool),
        ("no_timestamps", ctypes.c_bool),
        ("single_segment", ctypes.c_bool),
        ("print_special", ctypes.c_bool),
        ("print_progress", ctypes.c_bool),
        ("print_realtime", ctypes.c_bool),
        ("print_timestamps", ctypes.c_bool),
        ("token_timestamps", ctypes.c_bool),
        ("thold_pt", ctypes.c_float),
        ("thold_ptsum", ctypes.c_float),
        ("max_len", ctypes.c_int),
        ("split_on_word", ctypes.c_bool),
        ("max_tokens", ctypes.c_int),
        ("debug_mode", ctypes.c_bool),
        ("audio_ctx", ctypes.c_int),
        ("tdrz_enable", ctypes.c_bool),
        ("suppress_regex", ctypes.c_char_p),
        ("initial_prompt", ctypes.c_char_p),
        ("carry_initial_prompt", ctypes.c_bool),
        ("prompt_tokens", ctypes.c_void_p),
        ("prompt_n_tokens", ctypes.c_int),
        ("language", ctypes.c_char_p),
        ("detect_language", ctypes.c_bool),
        ("suppress_blank", ctypes.c_bool),
        ("suppress_nst", ctypes.c_bool),
        ("temperature", ctypes.c_float),
        ("max_initial_ts", ctypes.c_float),
        ("length_penalty", ctypes.c_float),
        ("temperature_inc", ctypes.c_float),
        ("entropy_thold", ctypes.c_float),
        ("logprob_thold", ctypes.c_float),
        ("no_speech_thold", ctypes.c_float),
        ("greedy", _WhisperGreedyParams),
        ("beam_search", _WhisperBeamSearchParams),
        ("new_segment_callback", ctypes.c_void_p),
        ("new_segment_callback_user_data", ctypes.c_void_p),
        ("progress_callback", ctypes.c_void_p),
        ("progress_callback_user_data", ctypes.c_void_p),
        ("encoder_begin_callback", ctypes.c_void_p),
        ("encoder_begin_callback_user_data", ctypes.c_void_p),
        ("abort_callback", ctypes.c_void_p),
        ("abort_callback_user_data", ctypes.c_void_p),
        ("logits_filter_callback", ctypes.c_void_p),
        ("logits_filter_callback_user_data", ctypes.c_void_p),
        ("grammar_rules", ctypes.c_void_p),
        ("n_grammar_rules", ctypes.c_size_t),
        ("i_start_rule", ctypes.c_size_t),
        ("grammar_penalty", ctypes.c_float),
        ("vad", ctypes.c_bool),
        ("vad_model_path", ctypes.c_char_p),
        ("vad_params", _WhisperVadParams),
    ]


def model_path(model) -> str:
    return model_store.model_file_path(model.key, model.local_filename)


def _sidecar_dir() -> str:
    if getattr(sys, "frozen", False):
        candidates = [
            os.path.join(sys._MEIPASS, "whisper.cpp"),
            os.path.join(sys._MEIPASS, "whisper__dot__cpp"),
        ]
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
        return candidates[0]
    return os.path.join(os.getcwd(), "vendor", "whisper.cpp")


def binary_path() -> str:
    sidecar_dir = _sidecar_dir()
    candidates = [
        os.path.join(sidecar_dir, "whisper-cli"),
        os.path.join(sidecar_dir, "main"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError("whisper.cpp sidecar not found")


def _library_path() -> str:
    path = os.path.join(_sidecar_dir(), "libwhisper.1.dylib")
    if os.path.exists(path):
        return path
    raise FileNotFoundError("libwhisper sidecar not found")


def _thread_count() -> int:
    configured = os.environ.get("VVRITE_WHISPER_THREADS")
    if configured:
        try:
            return max(1, int(configured))
        except ValueError:
            pass
    return max(4, min(os.cpu_count() or 4, 8))


def _configure_library(lib):
    if getattr(lib, "_vvrite_configured", False):
        return lib
    lib.whisper_context_default_params.restype = _WhisperContextParams
    lib.whisper_init_from_file_with_params.argtypes = [
        ctypes.c_char_p,
        _WhisperContextParams,
    ]
    lib.whisper_init_from_file_with_params.restype = ctypes.c_void_p
    lib.whisper_free.argtypes = [ctypes.c_void_p]
    lib.whisper_full_default_params.argtypes = [ctypes.c_int]
    lib.whisper_full_default_params.restype = _WhisperFullParams
    lib.whisper_full.argtypes = [
        ctypes.c_void_p,
        _WhisperFullParams,
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_int,
    ]
    lib.whisper_full.restype = ctypes.c_int
    lib.whisper_full_n_segments.argtypes = [ctypes.c_void_p]
    lib.whisper_full_n_segments.restype = ctypes.c_int
    lib.whisper_full_get_segment_text.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.whisper_full_get_segment_text.restype = ctypes.c_char_p
    lib._vvrite_configured = True
    return lib


def _load_library():
    return _configure_library(ctypes.CDLL(_library_path()))


def is_loaded() -> bool:
    with _lock:
        return _ctx is not None


def unload():
    global _ctx, _loaded_model_key
    with _lock:
        if _ctx is not None and _lib is not None:
            _lib.whisper_free(_ctx)
        _ctx = None
        _loaded_model_key = None


def load(model):
    global _lib, _ctx, _loaded_model_key
    with _lock:
        if _ctx is not None and _loaded_model_key == model.key:
            return
        unload()
        _lib = _load_library()
        params = _lib.whisper_context_default_params()
        params.use_gpu = True
        params.flash_attn = True
        path = model_path(model).encode("utf-8")
        _ctx = _lib.whisper_init_from_file_with_params(path, params)
        if not _ctx:
            _ctx = None
            raise RuntimeError(f"Failed to load Whisper model: {model_path(model)}")
        _loaded_model_key = model.key


def is_cached(model) -> bool:
    return os.path.exists(model_path(model))


def get_size(model) -> int:
    try:
        request = urllib.request.Request(model.download_url, method="HEAD")
        with urllib.request.urlopen(request, timeout=20) as response:
            return int(response.headers.get("Content-Length", "0"))
    except Exception:
        return 0


def download(model, progress_callback=None) -> str:
    dest = model_path(model)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = f"{dest}.download"
    request = urllib.request.Request(
        model.download_url,
        headers={"User-Agent": "vvrite"},
    )
    downloaded = 0
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            total = int(response.headers.get("Content-Length", "0") or "0")
            with open(tmp, "wb") as f:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback is not None:
                        progress_callback(downloaded, total)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    os.replace(tmp, dest)
    if progress_callback is not None and downloaded == 0:
        progress_callback(os.path.getsize(dest), os.path.getsize(dest))
    return dest


def _language_arg(prefs) -> str:
    if prefs.output_mode == OUTPUT_MODE_TRANSLATE_TO_ENGLISH:
        return "auto"
    if prefs.asr_language == "auto":
        return "auto"
    return str(prefs.asr_language)


def _clean_output(stdout: str) -> str:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    return "\n".join(lines).strip()


def _fast_cli_args() -> list[str]:
    return [
        "-t",
        str(_thread_count()),
        "-bs",
        "1",
        "-bo",
        "1",
        "-nf",
        "-np",
    ]


def _audio_context_for_samples(n_samples: int) -> int:
    override = os.environ.get("VVRITE_WHISPER_AUDIO_CTX")
    if override:
        try:
            return max(1, min(1500, int(override)))
        except ValueError:
            pass

    duration_seconds = max(0.0, n_samples / 16000.0)
    needed_frames = int(math.ceil(duration_seconds * 50.0)) + 64
    return max(256, min(1500, needed_frames))


def _make_full_params(prefs, n_samples: int):
    params = _lib.whisper_full_default_params(WHISPER_SAMPLING_GREEDY)
    params.n_threads = _thread_count()
    params.translate = prefs.output_mode == OUTPUT_MODE_TRANSLATE_TO_ENGLISH
    params.no_context = True
    params.no_timestamps = True
    params.single_segment = True
    params.print_special = False
    params.print_progress = False
    params.print_realtime = False
    params.print_timestamps = False
    params.audio_ctx = _audio_context_for_samples(n_samples)
    params.temperature = 0.0
    params.temperature_inc = 0.0
    params.greedy.best_of = 1
    params.beam_search.beam_size = 1

    keepalive = []
    language = _language_arg(prefs).encode("utf-8")
    params.language = language
    keepalive.append(language)

    custom_words = prefs.custom_words.strip()
    if custom_words:
        prompt = f"Use these spellings when relevant: {custom_words}".encode("utf-8")
        params.initial_prompt = prompt
        keepalive.append(prompt)

    return params, keepalive


def _coerce_samples(samples: np.ndarray) -> np.ndarray:
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim == 2:
        samples = samples.mean(axis=1, dtype=np.float32)
    return np.ascontiguousarray(samples, dtype=np.float32)


def _read_samples(path: str) -> tuple[np.ndarray, int]:
    samples, _sample_rate = sf.read(path, dtype="float32")
    return _coerce_samples(samples), int(_sample_rate)


def _resample_to_16khz(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    if sample_rate == 16000:
        return samples

    try:
        from scipy.signal import resample_poly

        divisor = math.gcd(sample_rate, 16000)
        resampled = resample_poly(samples, 16000 // divisor, sample_rate // divisor)
    except Exception:
        target_count = max(1, int(round(samples.size * 16000 / sample_rate)))
        source_x = np.linspace(0.0, 1.0, samples.size, endpoint=False)
        target_x = np.linspace(0.0, 1.0, target_count, endpoint=False)
        resampled = np.interp(target_x, source_x, samples)

    return np.ascontiguousarray(resampled, dtype=np.float32)


def _read_transcription_samples(raw_wav_path: str) -> tuple[np.ndarray, str | None]:
    try:
        samples, sample_rate = _read_samples(raw_wav_path)
        return _resample_to_16khz(samples, sample_rate), None
    except Exception:
        normalized_path = audio_utils.normalize(raw_wav_path)
        normalized_samples, _normalized_rate = _read_samples(normalized_path)
        return normalized_samples, normalized_path


def _transcribe_with_library(raw_wav_path: str, model, prefs) -> str:
    cleanup_path = None
    try:
        samples, cleanup_path = _read_transcription_samples(raw_wav_path)
        with _lock:
            if _ctx is None or _loaded_model_key != model.key:
                load(model)
            params, _keepalive = _make_full_params(prefs, int(samples.size))
            result = _lib.whisper_full(
                _ctx,
                params,
                samples.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                int(samples.size),
            )
            if result != 0:
                raise RuntimeError(f"whisper.cpp failed with code {result}")
            segment_count = _lib.whisper_full_n_segments(_ctx)
            text = "".join(
                (
                    _lib.whisper_full_get_segment_text(_ctx, i) or b""
                ).decode("utf-8", errors="replace")
                for i in range(segment_count)
            )
            return _clean_output(text)
    finally:
        for path in (raw_wav_path, cleanup_path):
            if path is None:
                continue
            try:
                os.unlink(path)
            except OSError:
                pass


def _transcribe_with_cli(raw_wav_path: str, model, prefs) -> str:
    normalized_path = audio_utils.normalize(raw_wav_path)
    try:
        args = [
            binary_path(),
            "-m",
            model_path(model),
            "-f",
            normalized_path,
            "--no-timestamps",
            "-l",
            _language_arg(prefs),
            *_fast_cli_args(),
        ]
        if prefs.output_mode == OUTPUT_MODE_TRANSLATE_TO_ENGLISH:
            args.append("--translate")
        custom_words = prefs.custom_words.strip()
        if custom_words:
            args.extend(["--prompt", f"Use these spellings when relevant: {custom_words}"])

        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "whisper.cpp failed")
        return _clean_output(completed.stdout)
    finally:
        for path in (raw_wav_path, normalized_path):
            try:
                os.unlink(path)
            except OSError:
                pass


def transcribe(raw_wav_path: str, model, prefs) -> str:
    with _lock:
        use_library = _ctx is not None and _loaded_model_key == model.key
    if use_library:
        return _transcribe_with_library(raw_wav_path, model, prefs)
    return _transcribe_with_cli(raw_wav_path, model, prefs)
