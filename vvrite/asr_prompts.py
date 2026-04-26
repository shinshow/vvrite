"""Shared ASR prompts for language-preserving transcription."""

PRESERVE_SOURCE_LANGUAGE_PROMPT = (
    "Transcribe exactly what was spoken. Preserve each spoken language as-is. "
    "Do not translate or localize. Keep English words in English, Korean words "
    "in Korean, and Japanese words in Japanese."
)


def transcription_prompt(custom_words: str = "") -> str:
    custom_words = (custom_words or "").strip()
    if not custom_words:
        return PRESERVE_SOURCE_LANGUAGE_PROMPT
    return (
        f"{PRESERVE_SOURCE_LANGUAGE_PROMPT} "
        f"Use these spellings when relevant: {custom_words}"
    )
