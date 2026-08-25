import math
from typing import List

from scipy.optimize import shgo

from .EQConfig import EQConfig
from .Measurement import Measurement
from .Smoothing import SmoothingFactor


def _err(target, current, boost):
    return 2 ** (abs(target - current - boost) / 10)


def _create_fun_to_minimize(target, spl):
    def fun(boost):
        try:
            boost = float(boost[0])
        except (TypeError, IndexError):
            boost = float(boost)

        errs = 0
        for level in spl:
            errs += _err(target, level, boost)
        return (1 / len(spl)) * errs
    return fun


def minimize(target, spl):
    if not spl:
        raise ValueError("At least one SPL value is required")

    fun_to_minimize = _create_fun_to_minimize(target, spl)
    lower = target - max(spl)
    upper = target - min(spl)
    if math.isclose(lower, upper):
        return lower

    result = shgo(fun_to_minimize, bounds=[(lower, upper)])
    if not result.success:
        raise RuntimeError(f"Boost optimization failed: {result.message}")
    return result.x[0]


def calc_boost(
        measurements: List[Measurement],
        hz_value,
        target_level,
        eq_config: EQConfig,
        frequency_range=None,
):
    if not measurements:
        raise ValueError("At least one measurement is required")

    if frequency_range is None:
        frequency_range = (
            max(measurement.curve.starting_freq for measurement in measurements),
            min(measurement.curve.max_frequency for measurement in measurements),
        )
    starting_freq, max_frequency = frequency_range
    if starting_freq >= max_frequency:
        raise ValueError("Measurements do not have an overlapping frequency range")

    normalized = (
        (math.log(hz_value) - math.log(starting_freq))
        / (math.log(max_frequency) - math.log(starting_freq))
    )
    boost = 0
    for i, smoothing_factor in enumerate(SmoothingFactor):
        sp_levels = [measurement.eval(hz_value, smoothing_factor) + boost for measurement in measurements]
        adjustment = minimize(target_level, sp_levels)
        boost = boost + adjustment * eq_config.weighting_fun(i, normalized)

    return round(boost, 1)

