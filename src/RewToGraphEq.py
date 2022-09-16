from typing import List

from Curve import Curve
from src import TargetCurves, EQConfig
from src.FileReader import curve_from_rew_file, get_files
from src.Measurement import Measurement
from src.Smoothing import SmoothingFactor
from src.Utils import median, std


def calc_next_boost_smoothed(
        measurements: List[Measurement],
        hz_value,
        target_level,
        current_boost,
        weighting_factor,
        smoothing_factor,
        std_influence
):
    sp_levels = [measurement.eval(hz_value, smoothing_factor) for measurement in measurements]
    current_level = median(sp_levels) + current_boost
    target_diff = target_level - current_level

    std_dev = std(sp_levels)
    if std_influence != 0:  # std and std_influence does influence next boost adjustment
        std_dev_factor = 1 / (1 + std_dev) ** (1 / (10 - std_influence))
    else:  # std does not influence next boost adjustment
        std_dev_factor = 1

    boost_adjustment = target_diff * weighting_factor * std_dev_factor
    return current_boost + boost_adjustment


def calc_boost(measurements: List[Measurement], hz_value, target_level, eq_config: EQConfig.EQConfig):
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
            smoothing_factor,
            eq_config.room_correction_config.std_influence
        )

    return round(boost, 1)


def calc_eq_curve(measurements: List[Measurement], target_curve: Curve, eq_config: EQConfig.EQConfig):
    """
    Calculates a Graphic Equalizer for multiple measurement and a target curve
    :param eq_config: configuration for the eq generation
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
    return Curve(eq_config.eq_points, eq_level)


def create_eq(
        measurements_dir: str = None,
        file_paths: List[str] = None,
        eq_config=EQConfig.default,
        target_curve=TargetCurves.linear()
):
    file_paths = get_files(dir_path=measurements_dir, file_paths=file_paths)

    measurements: List[Measurement] = list(
        map(Measurement,
            map(Curve.to_deviation_curve, map(curve_from_rew_file, file_paths))
            )
    )
    target_curve = TargetCurves.adjust_bass_target(target_curve, measurements)
    eq_curve = calc_eq_curve(measurements, target_curve, eq_config)
    return eq_curve


def get_graph_eq_str(
        measurements_dir: str = None,
        file_paths: List[str] = None,
        eq_config=EQConfig.default,
        target_curve=TargetCurves.linear()):
    eq = create_eq(measurements_dir, file_paths, eq_config, target_curve)
    return eq_config.format(eq)

