import math
from collections.abc import Iterable
from typing import List, Collection

from scipy.interpolate import interp1d

from . import Smoothing, Utils


class Curve:

    log = 2  # Base of the used logarithm

    def __init__(self, x, y,
                 interpolation_alg="linear",
                 centered_at=None,
                 fun=None):
        x = list(x)
        y = list(y)

        if len(x) != len(y):
            raise ValueError("x and y must contain the same number of values")
        if len(x) < 2:
            raise ValueError("A curve requires at least two points")
        if any(value <= 0 for value in x):
            raise ValueError("Frequencies must be greater than 0")
        if any(not math.isfinite(value) for value in x):
            raise ValueError("Frequencies must be finite")
        if any(not math.isfinite(value) for value in y):
            raise ValueError("Curve values must be finite")
        if any(left >= right for left, right in zip(x, x[1:])):
            raise ValueError("Frequencies must be strictly increasing")

        self.starting_freq = x[0]
        self.max_frequency = x[-1]
        self.centered_at = centered_at
        self._frequencies = tuple(x)
        self._values = tuple(y)

        if fun is None:
            x = [math.log(x_, Curve.log) for x_ in x]
            self.fun = interp1d(x, y, kind=interpolation_alg)
        else:
            self.fun = fun

    def __call__(self, *args, **kwargs):
        return self._eval_linear(*args)

    def _eval(self, input_args: List):
        if len(input_args) == 1:  # a caller with a single input expects a single output
            return self.fun(input_args[0])
        return list(  # otherwise return list
            map(self.fun, input_args)
        )

    def _eval_linear(self, *args):
        """
        Call with a non-logarithmic input value
        If an argument is above the interpolation range, it gets extrapolated with the closest
        value inside of the interpolation range.
        :param value:
        :return:
        """
        args = _reduce_args(*args)
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
                args
            ))

        return self._eval(log_values)

    def log_eval(self, *args):
        args = _reduce_args(*args)
        return self._eval(args)

    def draw(self, title="Frequency Response"):
        try:
            from matplotlib import pyplot
        except ImportError as exc:
            raise RuntimeError("Plotting requires matplotlib. Install it with `pip install .[plot]`.") from exc

        # Plotting samples the interpolated curve for a smooth visualization; this
        # does not affect the curve's stored grid or any EQ calculation.
        x = Utils.log_spaced(self.starting_freq, self.max_frequency, 256)
        y = self(x)
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

    def smooth(self, smoothing_factor: Smoothing.SmoothingFactor):
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

    def to_deviation_curve(self, from_freq=100, to_freq=10000):
        if from_freq is None:
            from_freq = self.starting_freq
        if to_freq is None:
            to_freq = self.max_frequency
        if from_freq <= 0 or to_freq <= 0:
            raise ValueError("Reference frequencies must be greater than 0")
        if from_freq >= to_freq:
            raise ValueError("Reference frequency range must be increasing")

        reference_from = max(from_freq, self.starting_freq)
        reference_to = min(to_freq, self.max_frequency)
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
    def domain_frequencies(self):
        return list(self._frequencies)

    @property
    def domain_values(self):
        return list(self._values)

    def __add__(self, other):
        start = max(self.starting_freq, other.starting_freq)
        end = min(self.max_frequency, other.max_frequency)
        if start >= end:
            raise ValueError("Curves do not have an overlapping frequency range")
        points = _merged_frequency_grid(self, other, start, end)
        y = [self(point) + other(point) for point in points]
        return Curve(points, y)

    def __sub__(self, other):
        start = max(self.starting_freq, other.starting_freq)
        end = min(self.max_frequency, other.max_frequency)
        if start >= end:
            raise ValueError("Curves do not have an overlapping frequency range")
        points = _merged_frequency_grid(self, other, start, end)
        y = [self(point) - other(point) for point in points]
        return Curve(points, y)

    @classmethod
    def build_average_curve(cls, curves: Collection['Curve'], smoothing_factor=Smoothing.SmoothingFactor.NO_SMOOTHING):
        curves = list(curves)
        if not curves:
            raise ValueError("At least one curve is required")

        if smoothing_factor != smoothing_factor.NO_SMOOTHING:
            curves = [c.smooth(smoothing_factor) for c in curves]
        y = []
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


def _merged_frequency_grid(left, right, start, end):
    return sorted({
        frequency
        for curve in (left, right)
        for frequency in curve._frequencies
        if start <= frequency <= end
    } | {start, end})


def _validate_frequency(value):
    if not math.isfinite(value):
        raise ValueError("Frequencies must be finite")
    if value <= 0:
        raise ValueError("Frequencies must be greater than 0")
    return value


def _reduce_args(*args):
    if len(args) == 1:
        value = args[0]
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return list(value)
        return [value]

    values = []
    for value in args:
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            values.extend(value)
        else:
            values.append(value)
    return values



