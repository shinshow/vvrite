"""ASR model registry and feature flags."""

from dataclasses import dataclass

OUTPUT_MODE_TRANSCRIBE = "transcribe"
OUTPUT_MODE_TRANSLATE_TO_ENGLISH = "translate_to_english"

BACKEND_QWEN_MLX = "qwen_mlx"
BACKEND_WHISPER_CPP = "whisper_cpp"
BACKEND_WHISPER_MLX = "whisper_mlx"

DEFAULT_ASR_MODEL_KEY = "qwen3_asr_1_7b_8bit"
MODEL_ALIASES = {
    "whisper_large_v3": "whisper_large_v3_turbo_4bit",
    "whisper_large_v3_turbo": "whisper_large_v3_turbo_4bit",
}

MODEL_SHORT_NAMES = {
    "qwen3_asr_1_7b_8bit": "Qwen 8-bit",
    "qwen3_asr_1_7b_bf16": "Qwen BF16",
    "whisper_small_4bit": "Whisper small",
    "whisper_large_v3_4bit": "Whisper large-v3",
    "whisper_large_v3_turbo_4bit": "Whisper Turbo",
}


@dataclass(frozen=True)
class AsrModel:
    key: str
    display_name: str
    backend: str
    model_id: str
    download_url: str | None
    local_filename: str | None
    size_hint: str
    supports_language_hint: bool
    supports_translation_to_english: bool


ASR_MODELS = {
    "qwen3_asr_1_7b_8bit": AsrModel(
        key="qwen3_asr_1_7b_8bit",
        display_name="Qwen3-ASR 1.7B 8-bit",
        backend=BACKEND_QWEN_MLX,
        model_id="mlx-community/Qwen3-ASR-1.7B-8bit",
        download_url=None,
        local_filename=None,
        size_hint="~2.5 GB",
        supports_language_hint=True,
        supports_translation_to_english=False,
    ),
    "qwen3_asr_1_7b_bf16": AsrModel(
        key="qwen3_asr_1_7b_bf16",
        display_name="Qwen3-ASR 1.7B BF16 MLX",
        backend=BACKEND_QWEN_MLX,
        model_id="mlx-community/Qwen3-ASR-1.7B-bf16",
        download_url=None,
        local_filename=None,
        size_hint="~4.08 GB",
        supports_language_hint=True,
        supports_translation_to_english=False,
    ),
    "whisper_small_4bit": AsrModel(
        key="whisper_small_4bit",
        display_name="Whisper small 4-bit MLX",
        backend=BACKEND_WHISPER_MLX,
        model_id="mlx-community/whisper-small-4bit",
        download_url=None,
        local_filename=None,
        size_hint="~139 MB",
        supports_language_hint=True,
        supports_translation_to_english=True,
    ),
    "whisper_large_v3_4bit": AsrModel(
        key="whisper_large_v3_4bit",
        display_name="Whisper large-v3 4-bit MLX",
        backend=BACKEND_WHISPER_MLX,
        model_id="mlx-community/whisper-large-v3-4bit",
        download_url=None,
        local_filename=None,
        size_hint="~878 MB",
        supports_language_hint=True,
        supports_translation_to_english=True,
    ),
    "whisper_large_v3_turbo_4bit": AsrModel(
        key="whisper_large_v3_turbo_4bit",
        display_name="Whisper large-v3-turbo 4-bit MLX",
        backend=BACKEND_WHISPER_MLX,
        model_id="mlx-community/whisper-large-v3-turbo-4bit",
        download_url=None,
        local_filename=None,
        size_hint="~463 MB",
        supports_language_hint=True,
        supports_translation_to_english=False,
    ),
}


def get_model(key: str | None) -> AsrModel:
    canonical_key = MODEL_ALIASES.get(key or "", key or "")
    return ASR_MODELS.get(canonical_key, ASR_MODELS[DEFAULT_ASR_MODEL_KEY])


def model_short_name(key: str | None) -> str:
    model = get_model(key)
    return MODEL_SHORT_NAMES.get(model.key, model.display_name)


def is_output_mode_supported(model_key: str, output_mode: str) -> bool:
    model = get_model(model_key)
    if output_mode == OUTPUT_MODE_TRANSCRIBE:
        return True
    if output_mode == OUTPUT_MODE_TRANSLATE_TO_ENGLISH:
        return model.supports_translation_to_english
    return False
