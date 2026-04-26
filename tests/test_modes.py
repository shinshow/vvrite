"""Tests for output modes."""

import unittest

from vvrite.modes import get_mode, list_modes, post_process_for_mode


class TestModes(unittest.TestCase):
    def test_default_modes_exist(self):
        keys = [mode.key for mode in list_modes()]

        self.assertEqual(keys, ["voice", "message", "note", "email"])

    def test_unknown_mode_falls_back_to_voice(self):
        self.assertEqual(get_mode("missing").key, "voice")

    def test_message_mode_trims_text(self):
        self.assertEqual(post_process_for_mode("message", " hello  "), "hello")


if __name__ == "__main__":
    unittest.main()
