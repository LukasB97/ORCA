import math
from typing import List

from matplotlib import pyplot

from src import Curve, TargetCurves, EQConfig
from src.FileReader import curve_from_rew_file, get_files
from src.Measurement import Measurement
from src.Smoothing import SmoothingFactor
from src.Utils import median, median_std_dev, std


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
            normalized_eq[i] = normalized_eq[i] - highest_level
    return normalized_eq


def calc_next_boost_smoothed(
        measurements: List[Measurement],
        hz_value,
        target_level,
        current_boost,
        weighting_factor,
        smoothing_factor,
        std_dev_impact=0,
):
    """
    Adjusts the boost-level in regards to a collection of curves with a different smoothing factor
    :param std_dev_impact: in range 0-9, Determines the amount, to which the standard deviation of the spl at the hz_value
    across the measurements influences the change in boost level.
    A higher std_dev_impact will result in a lower boost adjustment
    :param smoothing_factor: smoothing factor to compute the next boost for
    :param weighting_factor: Factor to which the next spls adjustment contributes to the overall computed boost
    :param measurements: list of measurements
    :param hz_value: hz value to compute boost for
    :param target_level: The target spl for the hz value
    :param current_boost:
    :return:
    """
    spls = [measurement.eval(hz_value, smoothing_factor) for measurement in measurements]
    current_level = median(spls) + current_boost
    target_diff = target_level - current_level

    std_dev = std(spls)
    if std_dev_impact != 0:
        std_dev_factor = 1 / std_dev ** (1 / (10 - std_dev_impact))
    else:
        std_dev_factor = 1

    boost_adjustment = target_diff * weighting_factor * std_dev_factor
    return current_boost + boost_adjustment


def calc_boost(measurements: List[Measurement], hz_value, target_level, eq_config: EQConfig.EQConfig):
    """
    Calculates the db-boost for a single frequency
    :param target_level:
    :param measurements: List of measurements
    :param hz_value: hz value to calc eq for
    :return: db boost
    """

    log_pos = measurements[0].curve.get_log_from_hz(hz_value)
    log_max = len(measurements[0].curve.x)
    normalized = log_pos / log_max

    boost = 0
    for i, smoothing_factor in enumerate(SmoothingFactor):
        boost = calc_next_boost_smoothed(
            measurements,
            hz_value,
            target_level,
            boost,
            eq_config.room_correction_config.weighting_fun(i, normalized),
            smoothing_factor
        )

    return round(boost, 1)


def calc_eq_curve(measurements: List[Measurement], target_curve: Curve.Curve, eq_config: EQConfig.EQConfig):
    """
    Calculates a Graphic Equalizer for multiple measurement and a target curve
    :param eq_config:
    :param measurements: List of deviation curves
    :param target_curve: A curve that represents the eq target
    :return: List of db-boost values for each point in eq_points
    """
    eq_level = []

    for hz_value in eq_config.eq_points:
        eq_level.append(
            calc_boost(
                measurements,
                hz_value,
                target_curve(hz_value),
                eq_config
            )
        )
    return eq_level


def create_eq(
        measurements_dir: str = None,
        file_paths: List[str] = None,
        eq_config=EQConfig.default(),
        target_curve=TargetCurves.linear()
):

    file_paths = get_files(dir_path=measurements_dir, file_paths=file_paths)

    measurements: List[Measurement] = list(
        map(Measurement,
            map(Curve.create_deviation_curve, map(curve_from_rew_file, file_paths))
            )
    )
    target_curve = TargetCurves.adjust_bass_target(target_curve, measurements)
    level_adjustments = calc_eq_curve(measurements, target_curve, eq_config)
    points = list(map(math.log2, eq_config.eq_points))
    pyplot.plot(points, level_adjustments)
    pyplot.show()
    return eq_config.format(level_adjustments)



create_eq(file_paths=["test1.txt"])

curve_ = curve_from_rew_file("test1.txt")
curve_ = Curve.create_deviation_curve(curve_)

curve_.draw()
