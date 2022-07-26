import math

import numpy as np
from matplotlib import pyplot
from scipy.interpolate import interpolate

from src import Smoothing, Utils
from Smoothing import smooth_curve
import matplotlib.pyplot as plt

class Curve:

    def __init__(self, x, y, convert_to_log=True, **kwargs):
        if convert_to_log:
            x, base, multiplier = Utils.convert_hz_to_log_scale(x)
            self.log_base = base
            self.log_multiplier = multiplier
        else:
            for key, value in kwargs.items():
                if key == "log_multiplier":
                    self.log_multiplier = value
                elif key == "log_base":
                    self.log_base = value

        self.x = x
        self.y = y
        self.fun = interpolate.interp1d(x, y, kind="cubic")
        print(self.fun(1))

    def get_hz_of_log_x(self, x):
        return Utils.log_to_hz(self.log_base, self.log_multiplier, x)


    def __call__(self, *args, **kwargs):
        """
        naive evaluation at x-value
        :param args:
        :param kwargs:
        :return:
        """
        return self.fun(args[0])

    def eval_at_log(self, value):
        """
        Call with a logarithmic input value
        :param value:
        :return:
        """
        if not hasattr(self, "log_base"):
            raise ValueError("The x-axis is not logarithmic")
        return self(value)

    def eval_linear(self, value):
        """
        Call with a non-logarithmic input value
        :param value:
        :return:
        """
        if not hasattr(self, "log_base"):
            return self(value)
        return self(Utils.hz_to_log(self.log_base, self.log_multiplier, value))

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
            log_multiplier=self.log_multiplier
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
        return self(eval_points) / len(eval_points)

    @staticmethod
    def create_target_curve(freq_to_boost: dict = None):
        assert len(freq_to_boost) >= 4
        if not freq_to_boost:
            freq_to_boost = []
        freqs= list(freq_to_boost.keys())
        freqs.sort()
        boost = []
        for freq in freqs:
            boost.append(freq_to_boost[freq])
        if len(freqs) < 4:
            freqs = [1, 2] + freqs + [30000, 300001]
            boost = [0, 0] + boost + [0, 0]
        for i in range(len(freqs)):
            freqs[i] = np.log(freqs[i])
        return Curve(freqs, boost, False)

