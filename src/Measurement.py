from typing import Dict

from src.Curve import Curve
from src.Smoothing import SmoothingFactor, smooth_curve


class Measurement:

    _curves: Dict[int, Curve]

    def __init__(self, curve):
        self._curves = dict()
        self._curves[0] = curve

    def eval(self, hz, smoothing_factor: SmoothingFactor = 0):
        if smoothing_factor.value in self._curves:
            return self._curves[smoothing_factor.value](hz)
        smoothed_curve = self._curves[0].smooth(smoothing_factor)
        self._curves[smoothing_factor.value] = smoothed_curve
        return smoothed_curve(hz)

    @property
    def curve(self):
        return self._curves[0]
