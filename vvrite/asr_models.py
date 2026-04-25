"""ASR model registry and feature flags."""

from dataclasses import dataclass

OUTPUT_MODE_TRANSCRIBE = "transcribe"
OUTPUT_MODE_TRANSLATE_TO_ENGLISH = "translate_to_english"

BACKEND_QWEN_MLX = "qwen_mlx"
BACKEND_WHISPER_CPP = "whisper_cpp"

DEFAULT_ASR_MODEL_KEY = "qwen3_asr_1_7b_8bit"


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
    "whisper_large_v3": AsrModel(
        key="whisper_large_v3",
        display_name="Whisper large-v3",
        backend=BACKEND_WHISPER_CPP,
        model_id="ggerganov/whisper.cpp/ggml-large-v3.bin",
        download_url=(
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
            "ggml-large-v3.bin"
        ),
        local_filename="ggml-large-v3.bin",
        size_hint="~2.9 GiB",
        supports_language_hint=True,
        supports_translation_to_english=True,
    ),
    "whisper_large_v3_turbo": AsrModel(
        key="whisper_large_v3_turbo",
        display_name="Whisper large-v3-turbo",
        backend=BACKEND_WHISPER_CPP,
        model_id="ggerganov/whisper.cpp/ggml-large-v3-turbo.bin",
        download_url=(
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
            "ggml-large-v3-turbo.bin"
        ),
        local_filename="ggml-large-v3-turbo.bin",
        size_hint="~1.5 GiB",
        supports_language_hint=True,
        supports_translation_to_english=False,
    ),
}


def get_model(key: str | None) -> AsrModel:
    return ASR_MODELS.get(key or "", ASR_MODELS[DEFAULT_ASR_MODEL_KEY])


def is_output_mode_supported(model_key: str, output_mode: str) -> bool:
    model = get_model(model_key)
    if output_mode == OUTPUT_MODE_TRANSCRIBE:
        return True
    if output_mode == OUTPUT_MODE_TRANSLATE_TO_ENGLISH:
        return model.supports_translation_to_english
    return False
