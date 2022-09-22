import operator
from collections.abc import Iterable
from functools import reduce
from typing import List

from matplotlib import pyplot
from scipy.interpolate import interpolate

from src import Smoothing, Utils
from src.Utils import log_to_hz


class Curve:

    def __init__(self, x, y, log_base=None, starting_freq=None, interpolation_alg="linear", centered_at=None):
        if not log_base or not starting_freq:
            self.starting_freq = x[0]
            x, base = Utils.convert_hz_to_log_scale(x)
            self.log_base = base
        else:
            self.log_base = log_base
            self.starting_freq = starting_freq
        self.centered_at = centered_at
        self.x = x
        self.y = y
        self.fun = interpolate.interp1d(x, y, kind=interpolation_alg)
        if len(x) < 0:
            xx = Utils.log_spaced_ints(starting_freq, starting_freq + x[-1])
            self.fun = interpolate.interp1d(
                xx,
                [fun(x_) for x_ in xx],
                kind=interpolation_alg)

    def get_log_from_hz(self, x):
        return Utils.hz_to_log(x, self.log_base, self.starting_freq)

    def __call__(self, *args, **kwargs):
        return self._eval_linear(*args)

    def _eval(self, input_args: List):
        if len(input_args) == 1:  # a caller with a single input expects a single output
            arg = input_args[0]
            return self.fun(input_args[0])
        return list(  # otherwise return list
            map(
                self.fun, input_args
            )
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
        log_values = list(  # convert Hz value to log scale
            map(
                lambda x: max(  # extrapolate values outside of the interpolation range with the closest value inside
                    # of the interpolation range
                    min(
                        Utils.hz_to_log(x, self.log_base, self.starting_freq),
                        self.x[-1]), 0
                ),
                args
            ))

        return self._eval(log_values)

    def log_eval(self, *args):
        args = _reduce_args(*args)
        return self._eval(args)

    def draw(self):
        x = Utils.log_spaced_ints(
            self.starting_freq, log_to_hz(self.x[-1], self.log_base, self.starting_freq), 256
        )
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
        pyplot.ylabel('dB adjustment', fontsize=12)
        pyplot.plot(x, y, color='blue')
        pyplot.xscale('log')
        pyplot.show()

    def smooth(self, smoothing_factor: Smoothing.SmoothingFactor):
        """
        Returns a new Curve object with smoothed y-values
        :param smoothing_factor:
        :return:
        """
        return Curve(
            self.x,
            Smoothing.smooth_1d(self.y, smoothing_factor),
            log_base=self.log_base,
            starting_freq=self.starting_freq
        )

    def to_deviation_curve(self, from_freq=100, to_freq=10000):
        points = Utils.log_spaced_ints(from_freq, to_freq, count=128)
        avg = sum(self(points)) / len(points)

        new_y = [elem - avg for elem in self.y]
        return Curve(
            x=self.x,
            y=new_y,
            log_base=self.log_base,
            starting_freq=self.starting_freq,
            centered_at=avg
        )

    def __add__(self, other):
        y = []
        for x in self.x:
            hz = self.starting_freq * self.log_base ** x
            y.append(self(hz) + other(hz))
        return Curve(
            self.x, y, log_base=self.log_base, starting_freq=self.starting_freq)




def _reduce_args(*args):
    args = reduce(operator.concat, args)  # If multiple collections are passed, merge
    if not isinstance(args, Iterable):  # If a single number argument is passed, wrap in list
        args = [args]
    return args
