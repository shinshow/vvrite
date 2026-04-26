"""Audio normalization for ASR input."""

import os
import tempfile

import numpy as np
import soundfile as sf

from vvrite.preferences import SAMPLE_RATE


def _to_mono(samples: np.ndarray) -> np.ndarray:
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim > 1:
        samples = samples.mean(axis=1, dtype=np.float32)
    return np.ascontiguousarray(samples, dtype=np.float32)


def _resample(samples: np.ndarray, source_rate: int) -> np.ndarray:
    if source_rate == SAMPLE_RATE:
        return samples
    if source_rate <= 0:
        raise ValueError(f"Invalid audio sample rate: {source_rate}")

    from scipy.signal import resample_poly

    divisor = np.gcd(source_rate, SAMPLE_RATE)
    resampled = resample_poly(
        samples,
        SAMPLE_RATE // divisor,
        source_rate // divisor,
    )
    return np.ascontiguousarray(resampled, dtype=np.float32)


def normalize(input_path: str) -> str:
    """
    Normalize audio to 16kHz mono PCM WAV for ASR.
    Returns path to the normalized temporary WAV file.
    """
    samples, source_rate = sf.read(input_path, dtype="float32", always_2d=False)
    normalized = _resample(_to_mono(samples), int(source_rate))

    fd, output_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    sf.write(output_path, normalized, SAMPLE_RATE, subtype="PCM_16")
    return output_path
