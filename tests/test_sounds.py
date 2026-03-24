"""Tests for sounds module."""
import unittest


class TestIsCustomPath(unittest.TestCase):
    def test_system_sound_name(self):
        from vvrite.sounds import is_custom_path
        self.assertFalse(is_custom_path("Glass"))

    def test_absolute_path(self):
        from vvrite.sounds import is_custom_path
        self.assertTrue(is_custom_path("/Users/foo/beep.wav"))

    def test_empty_string(self):
        from vvrite.sounds import is_custom_path
        self.assertFalse(is_custom_path(""))


class TestListSystemSounds(unittest.TestCase):
    def test_returns_sorted_list(self):
        from vvrite.sounds import list_system_sounds
        sounds = list_system_sounds()
        self.assertIsInstance(sounds, list)
        self.assertEqual(sounds, sorted(sounds))

    def test_contains_known_sounds(self):
        from vvrite.sounds import list_system_sounds
        sounds = list_system_sounds()
        # These are standard macOS system sounds
        self.assertIn("Glass", sounds)
        self.assertIn("Purr", sounds)

    def test_no_file_extensions(self):
        from vvrite.sounds import list_system_sounds
        sounds = list_system_sounds()
        for name in sounds:
            self.assertFalse(name.endswith(".aiff"), f"{name} has extension")


if __name__ == "__main__":
    unittest.main()
