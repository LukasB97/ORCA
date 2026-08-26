from __future__ import annotations

import math
from collections.abc import Callable, Collection

from scipy.optimize import minimize_scalar  # type: ignore[import-untyped]


def _err(target: float, current: float, boost: float) -> float:
    return 2 ** (abs(target - current - boost) / 10)


def _create_fun_to_minimize(
    target: float,
    spl: Collection[float],
) -> Callable[[float], float]:
    def fun(boost: float) -> float:
        errs = 0.0
        for level in spl:
            errs += _err(target, level, boost)
        return (1 / len(spl)) * errs

    return fun


def minimize(target: float, spl: Collection[float]) -> float:
    if not spl:
        raise ValueError("At least one SPL value is required")

    fun_to_minimize = _create_fun_to_minimize(target, spl)
    lower = target - max(spl)
    upper = target - min(spl)
    if math.isclose(lower, upper):
        return lower

    result = minimize_scalar(
        fun_to_minimize,
        bounds=(lower, upper),
        method="bounded",
    )
    if not result.success:
        raise RuntimeError(f"Boost optimization failed: {result.message}")
    return float(result.x)
