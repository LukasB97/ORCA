import math
from typing import List

from matplotlib import pyplot

from src import Curve, TargetCurves, EQConfig, Utils
from src.RewReader import read_hz_and_spl
from src.Smoothing import SMOOTHING_FACTOR




curves = dict()

def normalize_eq_boost(eq_level, max_boost):
    normalized_eq = []
    for i in range(len(eq_level)):
        if eq_level[i] > max_boost:
            normalized_eq.append(max_boost)
        else:
            normalized_eq.append(eq_level[i])
    highest_level = max(normalized_eq)
    if highest_level > 0:
        for i in range(len(normalized_eq)):
            normalized_eq[i] = normalized_eq[i] -highest_level
    return normalized_eq

def create_smoothe_curves(measured_curve: Curve.Curve):
    return [
        measured_curve.smooth(SMOOTHING_FACTOR.MAX_SMOOTHING),
        measured_curve.smooth(SMOOTHING_FACTOR.STRONG_SMOOTHING),
        measured_curve.smooth(SMOOTHING_FACTOR.DEFAULT_SMOOTHING),
        measured_curve.smooth(SMOOTHING_FACTOR.LIGHT_SMOOTHING),
        measured_curve.smooth(SMOOTHING_FACTOR.MIN_SMOOTHING),
        measured_curve.smooth(SMOOTHING_FACTOR.NO_SMOOTHING),
    ]


def calc_eq_curve(measured_curve: Curve.Curve, target_curve: Curve.Curve, eq_points: List[int]):
    target_volume = measured_curve.avg(0.6)
    eq_level = []
    smoothed_curves = create_smoothe_curves(measured_curve)
    for point in eq_points:
        eq_level.append(calc_boost(
            smoothed_curves,
            point,
            target_curve,
            target_volume
        ))
    return eq_level

def calc_weighting_factor(i, start, end):
    return 1 / (i * diff)


def calc_boost(measured_curves, point, target_curve: Curve.Curve, target_level):
    """
    Calculates the db-boost for a single frequency
    :param curves: List of curves, ordered by decreasing smooting factor
    :param x: Log Scaled frequency point
    :param point: the position in the x array, that we want to calculate the boost for
    :param target: target db level
    :return: db boost
    """
    def target_diff(level):
        return target_level + target_curve(point) - level

    boost = target_diff(measured_curves[0](point))
    normalized = (measured_curves[0].get_log_from_hz(point) - 0) / len(measured_curves[0].x)
    diff = 1.5 + normalized * 2
    print(diff)
    for i in range(1, len(measured_curves)):
        current_level = measured_curves[i](point) + boost
        current_deviation = target_diff(current_level)
        factor = 1 / (diff ** i)
        boost += factor * current_deviation
    #print("freq: ", point, " current level: ", measured_curves[-1](point), " boost: ", boost)
    return boost


def create_eq(file_path="test1.txt", config=EQConfig.default(), target_curve=TargetCurves.linear()):
    content = open(file_path, "r").read()
    freqs, spls = read_hz_and_spl(content)
    measurement = Curve.Curve(freqs, spls)
    measurement.draw()
    level_adjustments = calc_eq_curve(measurement, target_curve, eq_points=config._eq_points)
    points = list(map(math.log2, config._eq_points))
    pyplot.plot(points, level_adjustments)
    pyplot.show()
    return config.format(level_adjustments)

content = open("test1.txt", "r").read()
freqs, spls = read_hz_and_spl(content)
starting_freq = freqs[0]
x, base = Utils.convert_hz_to_log_scale(freqs)
for i in range(len(freqs)):
    print(abs(freqs[i] - Utils.log_to_hz(i, base, starting_freq)))

print(create_eq())
