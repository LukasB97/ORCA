import enum

import numpy as np
from scipy.ndimage import gaussian_filter1d


class SmoothingFactor(enum.Enum):
    MAX_SMOOTHING = 32
    STRONG_SMOOTHING = 16
    DEFAULT_SMOOTHING = 8
    LIGHT_SMOOTHING = 4
    MIN_SMOOTHING = 2
    NO_SMOOTHING = 0


_SIGMA_OCTAVES = {
    SmoothingFactor.MAX_SMOOTHING: 0.625,
    SmoothingFactor.STRONG_SMOOTHING: 0.3125,
    SmoothingFactor.DEFAULT_SMOOTHING: 0.15625,
    SmoothingFactor.LIGHT_SMOOTHING: 0.078125,
    SmoothingFactor.MIN_SMOOTHING: 0.0390625,
    SmoothingFactor.NO_SMOOTHING: 0.0,
}


def smooth_1d(frequencies, points, smoothing_factor: SmoothingFactor):
    """
    :param frequencies: logarithmically spaced frequencies for the values
    :param points: array of values to smooth
    :param smoothing_factor: Determines the strength of the smoothing process
    :return:
    """
    frequencies = np.asarray(frequencies, dtype=float)
    points = np.asarray(points, dtype=float)
    if frequencies.shape != points.shape:
        raise ValueError("frequencies and points must have the same shape")
    if smoothing_factor is SmoothingFactor.NO_SMOOTHING:
        return points.copy()

    octave_steps = np.diff(np.log2(frequencies))
    median_step = float(np.median(octave_steps))
    if not np.allclose(octave_steps, median_step, rtol=0.001, atol=0):
        raise ValueError("Smoothing requires a logarithmically uniform frequency grid")

    sigma_samples = _SIGMA_OCTAVES[smoothing_factor] / median_step
    return gaussian_filter1d(points, sigma=sigma_samples)
