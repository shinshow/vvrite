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


from unittest.mock import patch, MagicMock


class TestPlay(unittest.TestCase):
    @patch("vvrite.sounds.NSSound")
    def test_play_system_sound_with_volume(self, mock_nssound):
        from vvrite.sounds import play
        mock_sound = MagicMock()
        mock_copy = MagicMock()
        mock_sound.copy.return_value = mock_copy
        mock_nssound.soundNamed_.return_value = mock_sound

        play("Glass", volume=0.5)

        mock_nssound.soundNamed_.assert_called_once_with("Glass")
        mock_sound.copy.assert_called_once()
        mock_copy.setVolume_.assert_called_once_with(0.5)
        mock_copy.play.assert_called_once()

    @patch("vvrite.sounds.NSSound")
    def test_play_custom_file(self, mock_nssound):
        from vvrite.sounds import play
        mock_sound = MagicMock()
        mock_nssound.alloc.return_value.initWithContentsOfFile_byReference_.return_value = mock_sound

        play("/Users/foo/beep.wav", volume=0.7)

        mock_nssound.alloc.return_value.initWithContentsOfFile_byReference_.assert_called_once_with(
            "/Users/foo/beep.wav", True
        )
        mock_sound.setVolume_.assert_called_once_with(0.7)
        mock_sound.play.assert_called_once()

    @patch("vvrite.sounds.NSSound")
    def test_play_system_sound_not_found(self, mock_nssound):
        from vvrite.sounds import play
        mock_nssound.soundNamed_.return_value = None

        # Should not raise
        play("NonexistentSound", volume=1.0)

    @patch("vvrite.sounds.NSSound")
    def test_play_default_volume_is_one(self, mock_nssound):
        from vvrite.sounds import play
        mock_sound = MagicMock()
        mock_copy = MagicMock()
        mock_sound.copy.return_value = mock_copy
        mock_nssound.soundNamed_.return_value = mock_sound

        play("Glass")

        mock_copy.setVolume_.assert_called_once_with(1.0)


if __name__ == "__main__":
    unittest.main()
