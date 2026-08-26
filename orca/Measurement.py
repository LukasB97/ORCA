from __future__ import annotations

from collections.abc import Iterable
from typing import SupportsFloat, overload

from .Curve import Curve
from .Smoothing import SmoothingFactor


class Measurement:
    _curves: dict[int, Curve]

    def __init__(self, curve: Curve) -> None:
        self._curves = {}
        self._curves[0] = curve

    @overload
    def eval(
        self,
        hz: SupportsFloat,
        smoothing_factor: SmoothingFactor = SmoothingFactor.NO_SMOOTHING,
    ) -> float: ...

    @overload
    def eval(
        self,
        hz: Iterable[SupportsFloat],
        smoothing_factor: SmoothingFactor = SmoothingFactor.NO_SMOOTHING,
    ) -> list[float]: ...

    def eval(
        self,
        hz: SupportsFloat | Iterable[SupportsFloat],
        smoothing_factor: SmoothingFactor = SmoothingFactor.NO_SMOOTHING,
    ) -> float | list[float]:
        if smoothing_factor.value in self._curves:
            return self._curves[smoothing_factor.value](hz)
        smoothed_curve = self._curves[0].smooth(smoothing_factor)
        self._curves[smoothing_factor.value] = smoothed_curve
        return smoothed_curve(hz)

    @property
    def curve(self) -> Curve:
        return self._curves[0]
