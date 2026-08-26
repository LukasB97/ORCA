from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from numbers import Real
from typing import SupportsFloat

from . import WeightingFuns
from .Types import WeightingFunction
from .Utils import log_spaced_ints

_DEFAULT_WEIGHTING = WeightingFuns.linear()


@dataclass(frozen=True, init=False)
class EQConfig:
    """Validated, immutable settings for GraphicEQ generation."""

    eq_points: tuple[float, ...]
    max_boost: float
    set_max_zero: bool
    weighting_fun: WeightingFunction

    def __init__(
        self,
        eq_points: Iterable[SupportsFloat] | None = None,
        max_boost: SupportsFloat = 10.0,
        set_max_zero: bool = True,
        weighting_fun: WeightingFunction = _DEFAULT_WEIGHTING,
    ) -> None:
        points = log_spaced_ints(20, 20000, 128) if eq_points is None else eq_points

        try:
            normalized_points = tuple(float(point) for point in points)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("eq_points must contain numeric frequencies") from exc
        if len(normalized_points) < 2:
            raise ValueError("eq_points must contain at least two frequencies")
        if any(not math.isfinite(point) or point <= 0 for point in normalized_points):
            raise ValueError("eq_points must contain finite frequencies greater than 0")
        if any(left >= right for left, right in zip(normalized_points, normalized_points[1:])):
            raise ValueError("eq_points must be strictly increasing without duplicates")
        if not isinstance(set_max_zero, bool):
            raise ValueError("set_max_zero must be a boolean")
        if isinstance(max_boost, bool) or not isinstance(max_boost, Real):
            raise ValueError("max_boost must be a finite number")
        try:
            normalized_max_boost = float(max_boost)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("max_boost must be a finite number") from exc
        if not math.isfinite(normalized_max_boost):
            raise ValueError("max_boost must be a finite number")
        if normalized_max_boost != round(normalized_max_boost, 1):
            raise ValueError("max_boost must have at most one decimal place")
        if not callable(weighting_fun):
            raise ValueError("weighting_fun must be callable")

        object.__setattr__(self, "eq_points", normalized_points)
        object.__setattr__(self, "set_max_zero", set_max_zero)
        object.__setattr__(self, "max_boost", normalized_max_boost)
        object.__setattr__(self, "weighting_fun", weighting_fun)

    @classmethod
    def from_range(
        cls,
        eq_res: int = 128,
        eq_from: float = 20.0,
        eq_to: float = 20000.0,
        max_boost: SupportsFloat = 10.0,
        set_max_zero: bool = True,
        weighting_fun: WeightingFunction = _DEFAULT_WEIGHTING,
    ) -> EQConfig:
        """Create a config with logarithmically spaced integer control points."""
        return cls(
            eq_points=log_spaced_ints(eq_from, eq_to, eq_res),
            max_boost=max_boost,
            set_max_zero=set_max_zero,
            weighting_fun=weighting_fun,
        )
