from __future__ import annotations

import enum
from typing import cast

import numpy as np
from numpy.typing import ArrayLike
from scipy.ndimage import gaussian_filter1d  # type: ignore[import-untyped]

from .Types import FloatArray


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


def smooth_1d(
    frequencies: ArrayLike,
    points: ArrayLike,
    smoothing_factor: SmoothingFactor,
) -> FloatArray:
    """
    :param frequencies: logarithmically spaced frequencies for the values
    :param points: array of values to smooth
    :param smoothing_factor: Determines the strength of the smoothing process
    :return:
    """
    frequency_array = np.asarray(frequencies, dtype=float)
    point_array = np.asarray(points, dtype=float)
    if frequency_array.shape != point_array.shape:
        raise ValueError("frequencies and points must have the same shape")
    if smoothing_factor is SmoothingFactor.NO_SMOOTHING:
        return cast(FloatArray, point_array.copy())

    octave_steps = np.diff(np.log2(frequency_array))
    median_step = float(np.median(octave_steps))
    if not np.allclose(octave_steps, median_step, rtol=0.001, atol=0):
        raise ValueError("Smoothing requires a logarithmically uniform frequency grid")

    sigma_samples = _SIGMA_OCTAVES[smoothing_factor] / median_step
    return cast(FloatArray, gaussian_filter1d(point_array, sigma=sigma_samples))
