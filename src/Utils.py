import math

import numpy
import numpy as np


def concat_functions(f, g):
    def concatenated(x):
        return f(x) + g(x)
    return concatenated


def log_to_hz(value, base, start_value=1):
    return start_value * base ** value


def hz_to_log(value, base, starting_value=1):
    return math.log(value / starting_value, base)


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


def log_spaced_ints(start, end, count=128, domain_size=None):
    if end - start < count:
        raise ValueError("Cannot create 128 ints between "
                         + start + " and " + end)
    if not domain_size:
        domain_size = count
    ints = list(
        set(map(int, np.logspace(
            math.log10(start),
            math.log10(end),
            domain_size,
            endpoint=True
        )))
    )
    if len(ints) < count:
        next_domain_size = domain_size + count - len(ints)
        ints = log_spaced_ints(start, end, count=count, domain_size=next_domain_size)
    ints.sort()
    return ints


