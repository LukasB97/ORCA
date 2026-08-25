from __future__ import annotations

import math
from collections.abc import Callable, Collection, Iterable
from typing import SupportsFloat, cast, overload

from scipy.interpolate import interp1d  # type: ignore[import-untyped]

from . import Smoothing, Utils


class Curve:

    log = 2  # Base of the used logarithm

    def __init__(
        self,
        x: Iterable[SupportsFloat],
        y: Iterable[SupportsFloat],
        interpolation_alg: str = "linear",
        centered_at: float | None = None,
        fun: Callable[[float], SupportsFloat] | None = None,
    ) -> None:
        x_values = [float(value) for value in x]
        y_values = [float(value) for value in y]

        if len(x_values) != len(y_values):
            raise ValueError("x and y must contain the same number of values")
        if len(x_values) < 2:
            raise ValueError("A curve requires at least two points")
        if any(value <= 0 for value in x_values):
            raise ValueError("Frequencies must be greater than 0")
        if any(not math.isfinite(value) for value in x_values):
            raise ValueError("Frequencies must be finite")
        if any(not math.isfinite(value) for value in y_values):
            raise ValueError("Curve values must be finite")
        if any(left >= right for left, right in zip(x_values, x_values[1:])):
            raise ValueError("Frequencies must be strictly increasing")

        self.starting_freq: float = x_values[0]
        self.max_frequency: float = x_values[-1]
        self.centered_at: float | None = centered_at
        self._frequencies: tuple[float, ...] = tuple(x_values)
        self._values: tuple[float, ...] = tuple(y_values)

        if fun is None:
            log_x = [math.log(value, Curve.log) for value in x_values]
            self.fun = cast(
                Callable[[float], SupportsFloat],
                interp1d(log_x, y_values, kind=interpolation_alg),
            )
        else:
            self.fun = fun

    @overload
    def __call__(self, value: SupportsFloat, /) -> float:
        ...

    @overload
    def __call__(self, values: Iterable[SupportsFloat], /) -> list[float]:
        ...

    @overload
    def __call__(
        self,
        first: SupportsFloat,
        second: SupportsFloat,
        /,
        *rest: SupportsFloat,
    ) -> list[float]:
        ...

    def __call__(
        self,
        *args: object,
    ) -> float | list[float]:
        return self._eval_linear(*args)

    def _eval(self, input_args: list[float]) -> float | list[float]:
        if len(input_args) == 1:  # a caller with a single input expects a single output
            return float(self.fun(input_args[0]))
        return [float(self.fun(value)) for value in input_args]

    def _eval_linear(
        self,
        *args: object,
    ) -> float | list[float]:
        """
        Call with a non-logarithmic input value
        If an argument is above the interpolation range, it gets extrapolated with the closest
        value inside of the interpolation range.
        :param value:
        :return:
        """
        values = _reduce_args(*args)
        _max = math.log(self.max_frequency, Curve.log)
        _min = math.log(self.starting_freq, Curve.log)

        # convert Hz value to log scale and extrapolate values outside
        # of the interpolation range with the closest value inside
        # of the interpolation range
        log_values = list(
            map(
                lambda value: max(
                    min(math.log(_validate_frequency(value), Curve.log), _max),
                    _min),
                values
            ))

        return self._eval(log_values)

    @overload
    def log_eval(self, value: SupportsFloat, /) -> float:
        ...

    @overload
    def log_eval(self, values: Iterable[SupportsFloat], /) -> list[float]:
        ...

    @overload
    def log_eval(
        self,
        first: SupportsFloat,
        second: SupportsFloat,
        /,
        *rest: SupportsFloat,
    ) -> list[float]:
        ...

    def log_eval(
        self,
        *args: object,
    ) -> float | list[float]:
        values = _reduce_args(*args)
        return self._eval(values)

    def draw(self, title: str = "Frequency Response") -> None:
        try:
            from matplotlib import pyplot  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("Plotting requires matplotlib. Install it with `pip install .[plot]`.") from exc

        # Plotting samples the interpolated curve for a smooth visualization; this
        # does not affect the curve's stored grid or any EQ calculation.
        x = Utils.log_spaced(self.starting_freq, self.max_frequency, 256)
        y = cast(list[float], self(x))
        pyplot.figure(dpi=300, figsize=(8.4, 4.8))
        for i in range(1, 5):
            if 10 ** i > x[-1]:
                break
            pyplot.axvline(10 ** i, color='grey', lw=1)  # Add vertical line to improve readability

        current = 0
        while current >= min(y):
            current -= 5
        while current <= max(y):
            pyplot.axhline(current, color='grey', lw=1)  # Add horizontal line to improve readability
            current += 5

        pyplot.xlabel('Hz', fontsize=12)
        pyplot.ylabel('dB', fontsize=12)
        pyplot.plot(x, y, color='blue')
        pyplot.xscale('log')
        pyplot.title(title)

        pyplot.show()

    def smooth(self, smoothing_factor: Smoothing.SmoothingFactor) -> Curve:
        """
        Returns a new Curve object with smoothed y-values
        :param smoothing_factor:
        :return:
        """
        return Curve(
            self._frequencies,
            Smoothing.smooth_1d(
                self._frequencies,
                self._values,
                smoothing_factor,
            ),
        )

    def to_deviation_curve(
        self,
        from_freq: float | None = 100,
        to_freq: float | None = 10000,
    ) -> Curve:
        resolved_from = self.starting_freq if from_freq is None else from_freq
        resolved_to = self.max_frequency if to_freq is None else to_freq
        if resolved_from <= 0 or resolved_to <= 0:
            raise ValueError("Reference frequencies must be greater than 0")
        if resolved_from >= resolved_to:
            raise ValueError("Reference frequency range must be increasing")

        reference_from = max(resolved_from, self.starting_freq)
        reference_to = min(resolved_to, self.max_frequency)
        if reference_from >= reference_to:
            raise ValueError(
                "Reference frequency range does not overlap the curve domain"
            )

        points = [
            frequency for frequency in self._frequencies
            if reference_from <= frequency <= reference_to
        ]
        if not points:
            raise ValueError("Reference frequency range contains no curve points")
        avg = sum(self(points)) / len(points)

        y = [value - avg for value in self._values]
        return Curve(
            x=self._frequencies,
            y=y,
            centered_at=avg
        )

    @property
    def domain_frequencies(self) -> list[float]:
        return list(self._frequencies)

    @property
    def domain_values(self) -> list[float]:
        return list(self._values)

    def __add__(self, other: Curve) -> Curve:
        start = max(self.starting_freq, other.starting_freq)
        end = min(self.max_frequency, other.max_frequency)
        if start >= end:
            raise ValueError("Curves do not have an overlapping frequency range")
        points = _merged_frequency_grid(self, other, start, end)
        y = [self(point) + other(point) for point in points]
        return Curve(points, y)

    def __sub__(self, other: Curve) -> Curve:
        start = max(self.starting_freq, other.starting_freq)
        end = min(self.max_frequency, other.max_frequency)
        if start >= end:
            raise ValueError("Curves do not have an overlapping frequency range")
        points = _merged_frequency_grid(self, other, start, end)
        y = [self(point) - other(point) for point in points]
        return Curve(points, y)

    @classmethod
    def build_average_curve(
        cls,
        curves: Collection[Curve],
        smoothing_factor: Smoothing.SmoothingFactor = Smoothing.SmoothingFactor.NO_SMOOTHING,
    ) -> Curve:
        curves = list(curves)
        if not curves:
            raise ValueError("At least one curve is required")

        if smoothing_factor != smoothing_factor.NO_SMOOTHING:
            curves = [c.smooth(smoothing_factor) for c in curves]
        y: list[float] = []
        start = max(curve.starting_freq for curve in curves)
        end = min(curve.max_frequency for curve in curves)
        if start >= end:
            raise ValueError("Curves do not have an overlapping frequency range")

        points = sorted({
            frequency
            for curve in curves
            for frequency in curve._frequencies
            if start <= frequency <= end
        } | {start, end})
        for Hz in points:
            dbs = [c(Hz) for c in curves]
            avg = Utils.avg([10 ** (db / 10) for db in dbs])
            y.append(math.log10(avg) * 10)

        return Curve(points, y)


def _merged_frequency_grid(
    left: Curve,
    right: Curve,
    start: float,
    end: float,
) -> list[float]:
    return sorted({
        frequency
        for curve in (left, right)
        for frequency in curve._frequencies
        if start <= frequency <= end
    } | {start, end})


def _validate_frequency(value: SupportsFloat) -> float:
    frequency = float(value)
    if not math.isfinite(frequency):
        raise ValueError("Frequencies must be finite")
    if frequency <= 0:
        raise ValueError("Frequencies must be greater than 0")
    return frequency


def _reduce_args(
    *args: object,
) -> list[float]:
    if len(args) == 1:
        value = args[0]
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return [_coerce_float(item) for item in value]
        return [_coerce_float(value)]

    values: list[float] = []
    for value in args:
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            values.extend(_coerce_float(item) for item in value)
        else:
            values.append(_coerce_float(value))
    return values


def _coerce_float(value: object) -> float:
    return float(cast(SupportsFloat, value))



