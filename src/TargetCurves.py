import math

import numpy as np

from src.Curve import Curve
from src.Utils import hz_to_log

_DEFAULT_POINTS = np.logspace(0, math.log10(25000), 128, endpoint=True)
_DEFAULT_BASE = _DEFAULT_POINTS[-1] / _DEFAULT_POINTS[-2]
_DEFAULT_START = _DEFAULT_POINTS[0]


def _create_target_curve(freq_to_level: dict = None, interpolation_alg="linear"):
    if interpolation_alg != "linear" and len(freq_to_level) < 4:
        raise ValueError()
    if not freq_to_level:
        freq_to_level = []
    freqs = list(freq_to_level.keys())
    freqs.sort()
    boost = []
    for freq in freqs:
        boost.append(freq_to_level[freq])
    for i in range(len(freqs)):
        freqs[i] = hz_to_log(freqs[i], _DEFAULT_BASE, _DEFAULT_START)

    return Curve(freqs,
                 boost,
                 log_base=_DEFAULT_BASE,
                 starting_freq=_DEFAULT_START,
                 interpolation_alg=interpolation_alg
                 )


def linear():
    return _create_target_curve({
        1: 0,
        500: 0,
        4000: 0,
        25000: 0
    })


def downwards_slope(factor=1):
    return _create_target_curve({
        1: 0,
        20000: -10 * factor
    })


def downwards_slope_linear_upper_mids(factor=1):
    return _create_target_curve({
        1: 0,
        1000: -5 * factor,
        6000: -5 * factor,
        20000: -10 * factor,
        25000: -10 * factor
    })


def v_shape(factor=1):
    return _create_target_curve({
        1: -5,
        20: 0,
        100: 0,
        300: -5 * factor,
        3000: 0,
        10000: -5 * factor,
        20000: -10 * factor
    }, "quadratic")


def adjust_bass_target(target, measurements):
    print("TODO: adjust bass target")
    print(measurements)
    return target
