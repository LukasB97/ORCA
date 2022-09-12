import dataclasses
import math
from typing import Callable

import numpy as np

from src import WeightingFuns
from src.Utils import log_spaced_ints


@dataclasses.dataclass
class RoomCorrectionConfig:

    weighting_fun: Callable[[int, float], float] = WeightingFuns.default
    max_boost: int = 10
    on_target_freq: int = 60
    std_dev_impact: int = 3

    def __post_init__(self):
        if self.std_dev_impact > 9:
            raise ValueError("std_dev_impact must be in [0, ..., 9]")



@dataclasses.dataclass
class EQConfig:

    def __init__(self,
                 eq_res=None,
                 eq_points=None,
                 eq_from=20,
                 eq_to=20000,
                 formatter=None,
                 set_max_zero=True,
                 room_correction_config: RoomCorrectionConfig = RoomCorrectionConfig()
                 ):
        if not eq_points:
            if not eq_res:
                raise ValueError("Either eq_res or eq_points must be specified")
            eq_points = log_spaced_ints(eq_from, eq_to, eq_res)
        self.eq_points = eq_points
        self.formatter = formatter
        self.set_max_zero = set_max_zero
        self.room_correction_config = room_correction_config

    def format(self, level_adjustments, delimiter="; "):
        if len(level_adjustments) != len(self.eq_points):
            raise ValueError("Number of level adjustment entries must match the number of eq_points!")
        if self.formatter:
            return self.formatter(level_adjustments)
        str_adjustments = map(str, level_adjustments)
        points = map(str, self.eq_points)
        freq_boost_tuples = zip(points, str_adjustments)
        combo = map(" ".join, freq_boost_tuples)
        return "GraphicEQ: " + delimiter.join(combo)


def _get_wavelet_points():
    return [
        20, 21, 22, 23, 24, 26, 27, 29, 30, 32, 34, 36, 38, 40, 43, 45, 48, 50, 53, 56, 59, 63, 66, 70, 74, 78, 83, 87,
        92,
        97, 103, 109, 115, 121, 128, 136, 143, 151, 160, 169, 178, 188, 199, 210, 222, 235, 248, 262, 277, 292, 309,
        326,
        345, 364, 385, 406, 429, 453, 479, 506, 534, 565, 596, 630, 665, 703, 743, 784, 829, 875, 924, 977, 1032, 1090,
        1151, 1216, 1284, 1357, 1433, 1514, 1599, 1689, 1784, 1885, 1991, 2103, 2221, 2347, 2479, 2618, 2766, 2921,
        3086,
        3260, 3443, 3637, 3842, 4058, 4287, 4528, 4783, 5052, 5337, 5637, 5955, 6290, 6644, 7018, 7414, 7831, 8272,
        8738,
        9230, 9749, 10298, 10878, 11490, 12137, 12821, 13543, 14305, 15110, 15961, 16860, 17809, 18812, 19871
    ]


def wavelet():
    return EQConfig(eq_points=_get_wavelet_points())


def max_detail():
    return EQConfig(eq_res=256, eq_from=10, eq_to=25000)


def default():
    return EQConfig(eq_res=128)
