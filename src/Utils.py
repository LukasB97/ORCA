import math

import numpy
import numpy as np


def log_to_hz(value, base, start_value=1):
    return start_value * base ** value


def hz_to_log(value, base, starting_value=1):
    return math.log(value / starting_value, base)


def get_log_base(freqs):
    return freqs[-1] / freqs[-2]


def convert_hz_to_log_scale(freqs):
    base = get_log_base(freqs)
    log_x = []
    for i in range(len(freqs)):
        log_x.append(i)
    return log_x, base


def avg(elements):
    return sum(elements) / len(elements)


def median(elements):
    return numpy.median(elements)


def std(elements):
    return numpy.std(elements)

def log_spaced(start, end, count=128):
    return np.logspace(
        math.log10(start),
        math.log10(end),
        count,
        endpoint=True
    )

def log_spaced_ints(start, end, count=128):
    ints = list(
        set(map(int, np.logspace(
            math.log10(start),
            math.log10(end),
            count,
            endpoint=True
        )))
    )
    ints.sort()
    return ints


def median_std_dev(elements, d=False):
    m = median(elements)
    summed = 0
    for element in elements:
        if d:
            summed += element - m
        else:
            summed += abs(element - m)
    return summed / len(elements)
