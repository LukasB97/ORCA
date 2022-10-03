from typing import List

import Utils
from BoostComputation import calc_boost
from Curve import Curve, build_average_curve
from Smoothing import SmoothingFactor
from src import TargetCurves, EQConfig
from src.FileReader import curve_from_rew_file, get_files
from src.Measurement import Measurement


def calc_eq_curve(measurements: List[Measurement], target_curve: Curve, eq_config: EQConfig.EQConfig):
    """
    Calculates a Graphic Equalizer for multiple measurement and a target curve
    :param eq_config: configuration for the eq generation
    :param measurements: List of deviation curves
    :param target_curve: A curve that represents the eq target
    :return: List of db-boost values for each point in eq_points
    """
    eq_level = []
    eq_points = Utils.log_spaced(eq_config.eq_points[0], eq_config.eq_points[-1], 256)

    for hz_value in eq_points:
        eq_level.append(
            calc_boost(
                measurements,
                hz_value,
                target_curve(hz_value),
                eq_config
            )
        )
    return Curve(eq_points, eq_level)


def _estimate_avg_err(target: Curve, estimated_response: Curve, start):
    errs = []
    for point in estimated_response.domain_frequencies:
        errs.append(abs(target(point) - estimated_response(point)))

    med = round(Utils.median(errs), 1)
    print(start + " deviates ",
          med,
          " dB on average  dB from the target")
    return med


def create_eq(
        measurements_dir: str = None,
        file_paths: List[str] = None,
        eq_config=EQConfig.EQConfig(),
        target_curve=TargetCurves.linear()
):
    file_paths = get_files(dir_path=measurements_dir, file_paths=file_paths)
    curves = list(map(Curve.to_deviation_curve, map(curve_from_rew_file, file_paths)))

    avg = build_average_curve(curves)
    avg.smooth(SmoothingFactor.LIGHT_SMOOTHING).draw("Averaged Frequency Response of all Measurements")

    _estimate_avg_err(target_curve, avg, "The current fr")

    measurements = list(map(Measurement, curves))

    target_curve = TargetCurves.adjust_bass_target(target_curve, measurements)
    target_curve.draw("Target Curve")
    eq_curve = calc_eq_curve(measurements, target_curve, eq_config)

    estimated_fr = eq_curve + avg
    estimated_fr = estimated_fr.smooth(SmoothingFactor.LIGHT_SMOOTHING)
    estimated_fr.draw("Estimated Frequency Response after Equalization")

    _estimate_avg_err(target_curve, estimated_fr, "The estimated")

    return eq_curve


def format_eq_str(eq_curve: Curve, config=EQConfig.default()):
    level_adjustments = [level for level in eq_curve(config.eq_points)]
    level_adjustments = [min(level, config.max_boost) for level in level_adjustments]

    if config.set_max_zero:
        max_boost = max(level_adjustments)
        level_adjustments = [l - max_boost for l in level_adjustments]

    str_adjustments = ['%.1f' % level for level in level_adjustments]
    eq_points = map(str, config.eq_points)

    freq_boost_tuples = zip(eq_points, str_adjustments)
    combo = map(" ".join, freq_boost_tuples)

    return "GraphicEQ: " + "; ".join(combo)


def get_graph_eq_str(
        measurements_dir: str = None,
        file_paths: List[str] = None,
        eq_config=EQConfig.default(),
        target_curve=TargetCurves.linear()):
    eq = create_eq(measurements_dir, file_paths, eq_config, target_curve)
    return format_eq_str(eq, config=eq_config)
