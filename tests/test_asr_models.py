"""Tests for ASR model registry."""

import unittest

from vvrite.asr_models import (
    ASR_MODELS,
    DEFAULT_ASR_MODEL_KEY,
    OUTPUT_MODE_TRANSCRIBE,
    OUTPUT_MODE_TRANSLATE_TO_ENGLISH,
    get_model,
    is_output_mode_supported,
)


class TestAsrModels(unittest.TestCase):
    def test_default_model_is_qwen(self):
        self.assertEqual(DEFAULT_ASR_MODEL_KEY, "qwen3_asr_1_7b_8bit")
        self.assertEqual(get_model(DEFAULT_ASR_MODEL_KEY).backend, "qwen_mlx")

    def test_contains_three_selectable_models(self):
        self.assertEqual(
            set(ASR_MODELS),
            {
                "qwen3_asr_1_7b_8bit",
                "whisper_large_v3",
                "whisper_large_v3_turbo",
            },
        )

    def test_whisper_large_v3_supports_translation(self):
        self.assertTrue(
            is_output_mode_supported(
                "whisper_large_v3", OUTPUT_MODE_TRANSLATE_TO_ENGLISH
            )
        )

    def test_qwen_and_turbo_do_not_support_translation_mode(self):
        self.assertFalse(
            is_output_mode_supported(
                "qwen3_asr_1_7b_8bit", OUTPUT_MODE_TRANSLATE_TO_ENGLISH
            )
        )
        self.assertFalse(
            is_output_mode_supported(
                "whisper_large_v3_turbo", OUTPUT_MODE_TRANSLATE_TO_ENGLISH
            )
        )

    def test_all_models_support_transcription(self):
        for key in ASR_MODELS:
            self.assertTrue(is_output_mode_supported(key, OUTPUT_MODE_TRANSCRIBE))

    def test_unknown_model_falls_back_to_default(self):
        self.assertEqual(get_model("missing").key, DEFAULT_ASR_MODEL_KEY)


if __name__ == "__main__":
    unittest.main()
