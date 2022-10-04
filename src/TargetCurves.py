import Smoothing
import Utils
from src.Curve import Curve


def _create_target_curve(freq_to_level: dict = None, interpolation_alg="linear"):
    if interpolation_alg != "linear" and len(freq_to_level) < 4:
        raise ValueError()

    frequencies = list(freq_to_level.keys())
    frequencies.sort()
    boost = []
    for freq in frequencies:
        boost.append(freq_to_level[freq])

    return Curve(frequencies,
                 boost,
                 interpolation_alg=interpolation_alg
                 )


def linear():
    return _create_target_curve({
        1: 0,
        500: 0,
        4000: 0,
        25000: 0
    })


def downwards_slope(factor=1):
    return _create_target_curve({
        1: 0,
        20000: -10 * factor
    })


def downwards_slope_linear_upper_mids(factor=1):
    return _create_target_curve({
        1: 0,
        1000: -5 * factor,
        6000: -5 * factor,
        20000: -10 * factor,
        25000: -10 * factor
    })


def v_shape(factor=1):
    return _create_target_curve({
        1: -5,
        20: 0,
        100: 0,
        300: -5 * factor,
        3000: 0,
        10000: -5 * factor,
        20000: -10 * factor
    }, "quadratic")


def adjust_bass_target(target, measurements, max_boost=5, upper_bound=100):
    curves = [
        m.curve.smooth(Smoothing.SmoothingFactor.LIGHT_SMOOTHING) for m in measurements
    ]
    avg = Curve.build_average_curve(curves)
    frequencies = Utils.log_spaced(avg.starting_freq, avg.max_frequency, Curve.res)

    y = []
    for x in frequencies:
        if x <= upper_bound:
            if target(x) > (avg(x) + max_boost):
                y.append(avg(x) + max_boost)
                continue
        y.append(target(x))
    tc = Curve(frequencies, y)

    return tc
