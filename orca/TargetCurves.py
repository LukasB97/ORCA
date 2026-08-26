from __future__ import annotations

from collections.abc import Mapping, Sequence

from . import Smoothing
from .Curve import Curve
from .Measurement import Measurement


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
    upper_bound: float = 100,
) -> Curve:
    curves = [m.curve.smooth(Smoothing.SmoothingFactor.LIGHT_SMOOTHING) for m in measurements]
    avg = Curve.build_average_curve(curves)
    frequencies = avg.domain_frequencies

    y = []
    for x in frequencies:
        if x <= upper_bound:
            if target(x) > (avg(x) + max_boost):
                y.append(avg(x) + max_boost)
                continue
        y.append(target(x))
    tc = Curve(frequencies, y)

    return tc
