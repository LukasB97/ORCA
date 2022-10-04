import math
import operator
from collections.abc import Iterable
from functools import reduce
from typing import List, Collection

from matplotlib import pyplot
from scipy.interpolate import interpolate

from src import Smoothing, Utils


class Curve:

    res = 512  # Resolution of the curves
    log = 2  # Base of the used logarithm

    def __init__(self, x, y,
                 interpolation_alg="linear",
                 centered_at=None,
                 fun=None):
        self.starting_freq = x[0]
        self.max_frequency = x[-1]
        self.centered_at = centered_at

        if not fun:
            x = [math.log(x_, Curve.log) for x_ in x]
            self.fun = interpolate.interp1d(x, y, kind=interpolation_alg)
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
                lambda x: max(
                    min(math.log(x, Curve.log), _max),
                    _min),
                args
            ))

        return self._eval(log_values)

    def log_eval(self, *args):
        args = _reduce_args(*args)
        return self._eval(args)

    def draw(self, title="Frequency Response"):
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
        x = Utils.log_spaced(self.starting_freq, self.max_frequency, self.res)
        return Curve(
            x, Smoothing.smooth_1d(self(x), smoothing_factor)
        )

    def to_deviation_curve(self, from_freq=100, to_freq=10000):
        points = Utils.log_spaced(from_freq, to_freq, count=128)
        avg = sum(self(points)) / len(points)

        y = [self(x) - avg for x in self.domain_frequencies]
        return Curve(
            x=self.domain_frequencies,
            y=y,
            centered_at=avg
        )

    @property
    def domain_frequencies(self, count=None):
        if not count:
            count = self.res
        return Utils.log_spaced(self.starting_freq, self.max_frequency, count)

    def __add__(self, other):
        start = max(self.starting_freq, other.starting_freq)
        end = min(self.max_frequency, other.max_frequency)
        points = Utils.log_spaced(start, end, self.res)

        def new_fun(x):
            return self.fun(x) + other.fun(x)

        y = [new_fun(math.log(x, Curve.log)) for x in points]

        return Curve(points, y, fun=new_fun)

    def __sub__(self, other):
        start = max(self.starting_freq, other.starting_freq)
        end = min(self.max_frequency, other.max_frequency)
        points = Utils.log_spaced(start, end, self.res)

        def new_fun(x):
            return self.fun(x) - other.fun(x)

        y = [new_fun(math.log(x, Curve.log)) for x in points]

        return Curve(points, y, fun=new_fun)

    @classmethod
    def build_average_curve(cls, curves: Collection['Curve'], smoothing_factor=Smoothing.SmoothingFactor.NO_SMOOTHING):
        if smoothing_factor != smoothing_factor.NO_SMOOTHING:
            curves = [c.smooth(smoothing_factor) for c in curves]
        y = []
        points = curves[0].domain_frequencies
        for Hz in points:
            dbs = [c(Hz) for c in curves]
            avg = Utils.avg([cls.log ** (db / 10) for db in dbs])  # Transform log-scale
            y.append(math.log(avg, cls.log) * 10)

        return Curve(points, y)


def _reduce_args(*args):
    args = reduce(operator.concat, args)  # If multiple collections are passed, merge
    if not isinstance(args, Iterable):  # If a single number argument is passed, wrap in list
        args = [args]
    return args



