import math

import numpy as np

from src.Curve import Curve
from src.Utils import hz_to_log

DEFAULT_POINTS = np.logspace(0, math.log10(25000), 128, endpoint=True)
DEFAULT_BASE = DEFAULT_POINTS[-1] / DEFAULT_POINTS[-2]
DEFAULT_START = DEFAULT_POINTS[0]


def create_target_curve(freq_to_boost: dict = None):
    assert len(freq_to_boost) >= 4
    if not freq_to_boost:
        freq_to_boost = []
    freqs= list(freq_to_boost.keys())
    freqs.sort()
    boost = []
    for freq in freqs:
        boost.append(freq_to_boost[freq])
    if len(freqs) < 4:
        freqs = [1, 2] + freqs + [30000, 300001]
        boost = [0, 0] + boost + [0, 0]
    for i in range(len(freqs)):
        freqs[i] = hz_to_log(freqs[i], DEFAULT_BASE, DEFAULT_START)

    return Curve(freqs,
                 boost,
                 convert_to_log=False,
                 log_base=DEFAULT_BASE,
                 starting_freq=DEFAULT_START
                 )

def linear():
    return create_target_curve({
        1: 0,
        500: 0,
        4000: 0,
        25000: 0
    })

def downwards_slope(drop_off_freq=100, drop=-7.5):
    return Curve.create_target_curve({
        1: 0,
        drop_off_freq: 0,
        20000: drop,
        25000: drop
    })

def downwards_slope_linear_upper_mids(drop_off_freq=100, drop=-7.5):
    return Curve.create_target_curve({
        1: 0,
        drop_off_freq: 0,
        20000: drop,
        25000: drop
    })

def v_shape(boost=5):
    return Curve.create_target_curve({
        1: 0,
        100: boost,
        300: (-1) * boost,
        800: 0,
        3000: boost,
        10000: 0,
        20000: -5
    })