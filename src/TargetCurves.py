import math
from typing import List

import numpy as np
from scipy.interpolate import interpolate
from scipy.optimize import differential_evolution

import Smoothing
import Utils
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


def minimize(curves: List[Curve], frequencies):
    def to_min(args):
        m = args[0]
        a = args[1]

        err = 0
        for freq in frequencies:
            for curve in curves:
                err += (
                               curve(freq) - (m * (math.log2(freq)) + a)
                       ) ** 2
        return err

    y_min = min([min(curve.y) for curve in curves])
    y_max = max([max(curve.y) for curve in curves])

    bounds = [(0, 2), (2 * y_min, 2 * y_max)]
    res = differential_evolution(func=to_min, bounds=bounds)
    return res.x[0], res.x[1]


def _get_minimizing_curve(adjust_to: List[Curve], frequencies, all_x=None):
    m, a = minimize(adjust_to, frequencies)

    def fun(_x):
        return m * math.log2(_x) + a

    if all_x is not None:
        x = all_x
    else:
        x = frequencies
    y = [fun(x_) for x_ in x]

    return Curve(x, y)


def split(fun, curves, frequencies):
    larger = []
    smaller = []
    for freq in frequencies:
        avg = Utils.avg([c(freq) for c in curves])
        if fun(freq) > avg:
            smaller.append(freq)
        elif fun(freq) < avg:
            larger.append(freq)
    return smaller, larger


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def adjust_target(target: Curve, adjust_to: List[Curve], max_boost, split_into=8, upper_bound=80):
    size = math.ceil(128.0 / split_into)
    frequencies = Utils.log_spaced(adjust_to[0].starting_freq, upper_bound, size * split_into)
    minimizing_curves = [
        _get_minimizing_curve(adjust_to, f, frequencies) for f in chunks(frequencies, size)
    ]

    y = []
    for i, vals in enumerate(chunks(frequencies, size)):
        for x in vals:
            y.append(minimizing_curves[i](x))
    mc = Curve(frequencies, y)
    mid_freqs = [frequencies[0]]
    for i in range(split_into):
        mid_freqs.append(i * size + size / 2)
    mid_freqs.append(frequencies[-1])
    yy = [mc(x) + max_boost for x in mid_freqs]
    fun = interpolate.interp1d(mid_freqs, yy, kind="quadratic")

    y = []
    frequencies = Utils.log_spaced(adjust_to[0].starting_freq, 25000, 128)
    for x in frequencies:
        if x <= upper_bound:
            if target(x) > fun(x):
                y.append(fun(x))
                continue
        y.append(target(x))
    tc = Curve(frequencies, y)

    return tc


def adjust_bass_target(target, measurements, max_boost=5):
    curves = [
        m.curve.smooth(Smoothing.SmoothingFactor.LIGHT_SMOOTHING) for m in measurements
    ]
    return adjust_target(target, curves, max_boost=max_boost)
