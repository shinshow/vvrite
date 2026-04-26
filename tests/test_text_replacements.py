"""Tests for post-transcription replacement rules."""

import unittest

from vvrite.text_replacements import parse_replacements_text


class TestReplacementParsing(unittest.TestCase):
    def test_parse_replacements_accepts_arrow_and_comma_lines(self):
        text = """
        큐엔 -> Qwen
        브이라이트,vvrite
        malformed line
        큐엔 -> Qwen
        """

        rules = parse_replacements_text(text)

        self.assertEqual(
            rules,
            [
                ("큐엔", "Qwen"),
                ("브이라이트", "vvrite"),
            ],
        )

    def test_parse_replacements_ignores_empty_sides(self):
        rules = parse_replacements_text(" -> Qwen\nOpenAI -> \n")

        self.assertEqual(rules, [])


from vvrite.text_replacements import apply_replacements


class TestReplacementApplication(unittest.TestCase):
    def test_apply_replacements_is_case_insensitive(self):
        result = apply_replacements(
            "큐엔 모델과 OPEN AI를 사용합니다.",
            [("큐엔", "Qwen"), ("open ai", "OpenAI")],
        )

        self.assertEqual(result, "Qwen 모델과 OpenAI를 사용합니다.")

    def test_apply_replacements_respects_word_boundaries_for_ascii(self):
        result = apply_replacements(
            "todo and methodology",
            [("todo", "TODO")],
        )

        self.assertEqual(result, "TODO and methodology")


if __name__ == "__main__":
    unittest.main()
