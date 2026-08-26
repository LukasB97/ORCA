"""Weighting functions receive an iteration index and a normalized frequency."""

from __future__ import annotations

from .Types import WeightingFunction


def no_smoothing() -> WeightingFunction:
    def f(iteration: int, pos: float) -> float:
        return 1

    return f


def linear(iteration_influence: float = 1.5) -> WeightingFunction:
    def f(iteration: int, pos: float) -> float:
        return float(1 / ((1.1 + pos) ** (1 + iteration * iteration_influence)))

    return f
