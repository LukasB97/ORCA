from typing import List

from scipy.optimize import shgo

from EQConfig import EQConfig
from Measurement import Measurement
from Smoothing import SmoothingFactor
from Utils import median, std


def _err(t, c, b):
    return 2 ** (abs(t - c - b) / 10)


def _create_fun_to_minimize(target, spl):
    def fun(boost):
        errs = 0
        for level in spl:
            errs += _err(target, level, boost)
        return (1 / len(spl)) * errs
    return fun


def minimize(target, spl):
    fun_to_minimize = _create_fun_to_minimize(target, spl)
    bounds = [(target - max(spl), target - min(spl))]
    return shgo(fun_to_minimize, bounds=bounds).x[0]

def calc_next_boost_smoothed(
        measurements: List[Measurement],
        hz_value,
        target_level,
        current_boost,
        weighting_factor,
        smoothing_factor,
        std_influence
):
    sp_levels = [measurement.eval(hz_value, smoothing_factor) for measurement in measurements]
    current_level = median(sp_levels) + current_boost
    target_diff = target_level - current_level

    std_dev = std(sp_levels)
    if std_influence != 0:  # std and std_influence does influence next boost adjustment
        std_dev_factor = 1 / (1 + std_dev) ** (1 / (10 - std_influence))
    else:  # std does not influence next boost adjustment
        std_dev_factor = 1

    boost_adjustment = target_diff * weighting_factor * std_dev_factor
    return current_boost + boost_adjustment


def calc_boost(measurements: List[Measurement], hz_value, target_level, eq_config: EQConfig.EQConfig):
    log_pos = measurements[0].curve.get_log_from_hz(hz_value)
    log_max = len(measurements[0].curve.x)
    normalized = log_pos / log_max

    boost = 0
    for i, smoothing_factor in enumerate(SmoothingFactor):
        boost = calc_next_boost_smoothed(
            measurements,
            hz_value,
            target_level,
            boost,
            eq_config.room_correction_config.weighting_fun(i, normalized),
            smoothing_factor,
            eq_config.room_correction_config.std_influence
        )

    return round(boost, 1)

