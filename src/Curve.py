import math
import operator
from collections import Iterable
from functools import reduce

import numpy as np
from matplotlib import pyplot
from scipy.interpolate import interpolate

from src import Smoothing, Utils
from Smoothing import smooth_curve
import matplotlib.pyplot as plt

class Curve:

    def __init__(self, x, y, convert_to_log=True, **kwargs):
        if convert_to_log:
            self.starting_freq = x[0]
            x, base = Utils.convert_hz_to_log_scale(x)
            self.log_base = base
        else:
            for key, value in kwargs.items():
                if key == "log_base":
                    self.log_base = value
                elif key == "starting_freq":
                    self.starting_freq = value

        self.x = x
        self.y = y
        self.fun = interpolate.interp1d(x, y, kind="cubic")
        print(self.fun(1))

    def get_hz_of_log_x(self, x):
        return Utils.log_to_hz(x, self.log_base, self.starting_freq)


    def get_log_from_hz(self, x):
        return Utils.hz_to_log(x, self.log_base, self.starting_freq)


    def __call__(self, *args, **kwargs):
        """
        naive evaluation at x-value
        :param args:
        :param kwargs:
        :return:
        """
        return self._eval_linear(*args)

    def _eval_linear(self, *args):
        """
        Call with a non-logarithmic input value
        :param value:
        :return:
        """
        args = reduce(operator.concat, args)
        if not isinstance(args, Iterable): # If a single number argument is passed
            args = [args]
        log_values = list(
            map(
            lambda x: min(
                Utils.hz_to_log(x, self.log_base, self.starting_freq),
                self.x[-1]
            ),
            args
        ))
        if len(log_values) == 1:
            return self.fun(log_values[0])
        return list(
            map(
                self.fun, log_values
            )
        )

    def draw(self, logarithmic=True):

        #x = []
        #for i in self.x:
        #    x.append(self.log_base * self.log_multiplier ** i)
        x = self.x
        if len(x) < 64:
            x = np.logspace(0, math.log10(max(self.x)), 128, endpoint=True)


        pyplot.plot(x, self.fun(x))
        #pyplot.yscale('log')
        pyplot.show()

    def smooth(self, smoothing_factor: Smoothing.SMOOTHING_FACTOR):
        """
        Returns a new Curve object with smoothed y-values
        :param smoothing_factor:
        :return:
        """
        return Curve(
            self.x,
            Smoothing.smooth_curve(self.y, smoothing_factor),
            convert_to_log=False,
            log_base=self.log_base,
            starting_freq=self.starting_freq
        )

    def avg(self, eval_range):
        """
        Estimates the average value of the curve.
        The evaluation is centered at the median x-value and the extension to the
        bounds is determined by the eval_range.
        :param eval_range:
        :return:
        """
        if 0 >= eval_range or eval_range > 1:
            raise ValueError("evaluation range must be in ]0,1]")
        start = math.floor((len(self.x) / 2) - len(self.x) * (eval_range / 2))
        end = math.floor((len(self.x) / 2) + len(self.x) * (eval_range / 2))
        eval_points = []
        for i in range(start, end):
            eval_points.append(self.x[i])
        return sum(self(eval_points)) / len(eval_points)




