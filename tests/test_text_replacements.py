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


if __name__ == "__main__":
    unittest.main()
