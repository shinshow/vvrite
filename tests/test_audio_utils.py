"""Tests for audio normalization."""

import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

from vvrite import audio_utils
from vvrite.preferences import SAMPLE_RATE


class TestAudioUtils(unittest.TestCase):
    def test_normalize_resamples_to_16khz_mono_without_ffmpeg(self):
        source_rate = 48000
        duration_seconds = 1
        left = np.linspace(-0.5, 0.5, source_rate * duration_seconds, dtype=np.float32)
        right = np.linspace(0.5, -0.5, source_rate * duration_seconds, dtype=np.float32)
        stereo = np.column_stack([left, right])

        fd, input_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        normalized_path = None
        try:
            sf.write(input_path, stereo, source_rate, subtype="PCM_16")

            with patch("subprocess.run", side_effect=AssertionError("ffmpeg invoked")):
                normalized_path = audio_utils.normalize(input_path)

            samples, sample_rate = sf.read(
                normalized_path, dtype="float32", always_2d=False
            )
            self.assertEqual(sample_rate, SAMPLE_RATE)
            self.assertEqual(samples.ndim, 1)
            self.assertEqual(samples.shape, (SAMPLE_RATE * duration_seconds,))
        finally:
            for path in (input_path, normalized_path):
                if path is None:
                    continue
                try:
                    os.unlink(path)
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main()
