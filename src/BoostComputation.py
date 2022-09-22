from typing import List

from scipy.optimize import shgo

from EQConfig import EQConfig
from Measurement import Measurement
from Smoothing import SmoothingFactor


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


def calc_boost(measurements: List[Measurement], hz_value, target_level, eq_config: EQConfig):
    log_pos = measurements[0].curve.get_log_from_hz(hz_value)
    log_max = len(measurements[0].curve.x)
    normalized = log_pos / log_max
    boost = 0

    for i, smoothing_factor in enumerate(SmoothingFactor):
        measurements[0].eval(hz_value, smoothing_factor)
        sp_levels = [measurement.eval(hz_value, smoothing_factor) + boost for measurement in measurements]
        adjustment = minimize(target_level, sp_levels)
        boost = boost + adjustment * eq_config.room_correction_config.weighting_fun(i, normalized)

    return round(boost, 1)

