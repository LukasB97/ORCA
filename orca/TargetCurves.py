from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import cast

import numpy as np

from . import Smoothing
from .Curve import Curve
from .Measurement import Measurement

_BASS_POLYNOMIAL_DEGREE = 3
_BASS_TRANSITION_HALF_OCTAVES = 1.0 / 6.0
_FULL_BOOST_DEVIATION_DB = 5.0
_BOOST_MULTIPLIER_EXPONENT = 3.090378786955402
_BOOST_MULTIPLIER_SCALE_DB = 10.079382891257131


def _first_target_crossing(
    frequencies: np.ndarray,
    deviations: np.ndarray,
    upper_bound: float,
) -> float | None:
    """Return the first interpolated frequency where response reaches the target."""
    for index, (frequency, deviation) in enumerate(zip(frequencies, deviations)):
        if frequency > upper_bound:
            break
        if deviation < 0:
            continue
        if index == 0 or deviations[index - 1] >= 0:
            return float(frequency)

        previous_frequency = frequencies[index - 1]
        previous_deviation = deviations[index - 1]
        fraction = -previous_deviation / (deviation - previous_deviation)
        previous_log = math.log2(previous_frequency)
        crossing_log = previous_log + fraction * (math.log2(frequency) - previous_log)
        return float(2.0**crossing_log)
    return None


def _boost_multiplier(deviation_db: float) -> float:
    """Reduce boost smoothly once the fitted response is far below target."""
    residual = max(0.0, deviation_db - _FULL_BOOST_DEVIATION_DB)
    return math.exp(
        -math.log(2.0) * (residual / _BOOST_MULTIPLIER_SCALE_DB) ** _BOOST_MULTIPLIER_EXPONENT
    )


def _cubic_bass_offset(
    frequencies: np.ndarray,
    deviations: np.ndarray,
    crossing: float,
    max_boost: float,
) -> np.ndarray | None:
    """Fit and lift a crossing-anchored cubic on a log-frequency axis."""
    crossing_log = math.log2(crossing)
    fit_mask = frequencies < crossing
    fit_x = np.log2(frequencies[fit_mask]) - crossing_log
    fit_y = deviations[fit_mask]
    if len(fit_x) < _BASS_POLYNOMIAL_DEGREE + 1:
        return None

    design = np.column_stack([fit_x**power for power in range(1, _BASS_POLYNOMIAL_DEGREE + 1)])
    coefficients, *_ = np.linalg.lstsq(design, fit_y, rcond=None)

    def polynomial(relative_log_frequency: float) -> float:
        return float(
            sum(
                coefficient * relative_log_frequency**power
                for power, coefficient in enumerate(coefficients, start=1)
            )
        )

    def lifted(relative_log_frequency: float) -> float:
        fitted_deviation = min(0.0, polynomial(relative_log_frequency))
        distance = -fitted_deviation
        return fitted_deviation + max_boost * _boost_multiplier(distance)

    start_log = math.log2(float(frequencies[0]))
    search_points = np.linspace(start_log, crossing_log, 512)
    search_values = [lifted(float(value - crossing_log)) for value in search_points]
    center_log: float | None = None
    for left_index, right_value in enumerate(search_values[1:]):
        left_value = search_values[left_index]
        if left_value < 0 <= right_value:
            left_log = float(search_points[left_index])
            right_log = float(search_points[left_index + 1])
            fraction = -left_value / (right_value - left_value)
            center_log = left_log + fraction * (right_log - left_log)
            break
    if center_log is None:
        if search_values[0] >= 0:
            return cast(np.ndarray, np.zeros_like(frequencies))
        center_log = crossing_log

    transition_left = center_log - _BASS_TRANSITION_HALF_OCTAVES
    transition_right = center_log + _BASS_TRANSITION_HALF_OCTAVES
    transition_width = transition_right - transition_left
    left_relative = transition_left - crossing_log
    left_level = lifted(left_relative)
    derivative_step = 1e-5
    left_slope = (
        lifted(left_relative + derivative_step) - lifted(left_relative - derivative_step)
    ) / (2.0 * derivative_step)

    offsets: list[float] = []
    for frequency in frequencies:
        log_frequency = math.log2(float(frequency))
        relative = log_frequency - crossing_log
        if log_frequency <= transition_left:
            offset = lifted(relative)
        elif log_frequency >= transition_right:
            offset = 0.0
        else:
            position = (log_frequency - transition_left) / transition_width
            h00 = 2.0 * position**3 - 3.0 * position**2 + 1.0
            h10 = position**3 - 2.0 * position**2 + position
            offset = h00 * left_level + h10 * transition_width * left_slope
        offsets.append(min(0.0, offset))
    return cast(np.ndarray, np.asarray(offsets))


def _create_target_curve(
    freq_to_level: Mapping[float, float],
    interpolation_alg: str = "linear",
) -> Curve:
    if interpolation_alg != "linear" and len(freq_to_level) < 4:
        raise ValueError("Non-linear target curves require at least four points")

    frequencies = list(freq_to_level.keys())
    frequencies.sort()
    boost = []
    for freq in frequencies:
        boost.append(freq_to_level[freq])

    return Curve(frequencies, boost, interpolation_alg=interpolation_alg)


def linear() -> Curve:
    return _create_target_curve({1: 0, 500: 0, 4000: 0, 25000: 0})


def downwards_slope(factor: float = 1) -> Curve:
    return _create_target_curve({1: 0, 20000: -10 * factor})


def downwards_slope_linear_upper_mids(factor: float = 1) -> Curve:
    return _create_target_curve(
        {1: 0, 1000: -5 * factor, 6000: -5 * factor, 20000: -10 * factor, 25000: -10 * factor}
    )


def v_shape(factor: float = 1) -> Curve:
    return _create_target_curve(
        {1: -5, 20: 0, 100: 0, 300: -5 * factor, 3000: 0, 10000: -5 * factor, 20000: -10 * factor},
        "quadratic",
    )


def adjust_bass_target(
    target: Curve,
    measurements: Sequence[Measurement],
    max_boost: float = 5,
    upper_bound: float = 200,
) -> Curve:
    """Adapt the target to a smooth estimate of the speaker's bass extension.

    A cubic polynomial is fitted to the averaged response-to-target deviation
    from the measurement's lower bound to its first target crossing. The fitted
    extension is lifted by at most ``max_boost``; that lift fades smoothly for
    deviations beyond 5 dB so deeply attenuated bass receives almost no boost.
    """
    curves = [m.curve.smooth(Smoothing.SmoothingFactor.LIGHT_SMOOTHING) for m in measurements]
    avg = Curve.build_average_curve(curves)
    frequencies = np.asarray(avg.domain_frequencies)
    target_levels = np.asarray(target(frequencies))
    deviations = np.asarray(avg.domain_values) - target_levels
    crossing = _first_target_crossing(frequencies, deviations, upper_bound)
    if crossing is None or crossing <= frequencies[0]:
        return Curve(frequencies, target_levels)

    offsets = _cubic_bass_offset(frequencies, deviations, crossing, max_boost)
    if offsets is None:
        return Curve(frequencies, target_levels)
    return Curve(frequencies, target_levels + offsets)
