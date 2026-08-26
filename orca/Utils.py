from __future__ import annotations

import math
from collections.abc import Collection

import numpy as np

from .Types import FloatArray


def avg(elements: Collection[float]) -> float:
    return sum(elements) / len(elements)


def log_spaced(start: float, end: float, count: int = 128) -> FloatArray:
    return np.logspace(math.log10(start), math.log10(end), count, endpoint=True)


def log_spaced_ints(
    start: float,
    end: float,
    count: int = 128,
    domain_size: int | None = None,
) -> list[int]:
    if not math.isfinite(start) or not math.isfinite(end):
        raise ValueError("Frequency bounds must be finite")
    if start <= 0 or end <= 0:
        raise ValueError("Frequency bounds must be greater than 0")
    if start >= end:
        raise ValueError("Frequency bounds must be increasing")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("count must be a positive integer")

    first_int = math.ceil(start)
    last_int = math.floor(end)
    if last_int - first_int + 1 < count:
        raise ValueError(f"Cannot create {count} ints between {start} and {end}")

    if domain_size is None:
        domain_size = count
    if not isinstance(domain_size, int) or isinstance(domain_size, bool) or domain_size < 1:
        raise ValueError("domain_size must be a positive integer")

    while True:
        int_set = {
            max(first_int, min(last_int, round(value)))
            for value in np.logspace(
                math.log10(start),
                math.log10(end),
                domain_size,
                endpoint=True,
            )
        }
        int_set.update((first_int, last_int))
        ints = sorted(int_set)
        if len(ints) >= count:
            break
        domain_size += count - len(ints)

    if len(ints) > count:
        indices = np.linspace(0, len(ints) - 1, count)
        ints = [ints[round(index)] for index in indices]
    return ints
