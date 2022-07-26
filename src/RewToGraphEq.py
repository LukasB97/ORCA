from typing import List


from src import Curve, TargetCurves, EQConfig
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
        return target_level + target_curve.eval_linear(measured_curves[0].get_hz_of_log_x(point)) - level

    boost = target_diff(measured_curves[0](point))
    diff = 1 + (point / max(measured_curves[0].x))
    for i in range(1, len(curves)):
        current_level = curves[i](point) + boost
        current_deviation = target_diff(current_level)
        factor = 1 / (i * diff)
        boost += factor * current_deviation
    return boost


def create_eq(file_path="test1.txt", config=EQConfig.default(), target_curve=TargetCurves.linear()):
    content = open(file_path, "r").read()
    freqs, spls = read_hz_and_spl(content)
    measurement = Curve.Curve(freqs, spls)
    level_adjustments = calc_eq_curve(measurement, target_curve, eq_points=config._eq_points)
    return config.format(level_adjustments)



print(create_eq())
