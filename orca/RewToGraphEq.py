from typing import List

from . import TargetCurves, EQConfig, Utils
from .BoostComputation import calc_boost
from .Curve import Curve
from .FileReader import curve_from_rew_file, get_files
from .Measurement import Measurement
from .Smoothing import SmoothingFactor

REFERENCE_FROM = 100
REFERENCE_TO = 10000
EQ_POINT_RANGE_TOLERANCE = 0.02


def _get_common_frequency_range(curves: List[Curve]):
    curves = list(curves)
    if not curves:
        raise ValueError("At least one measurement is required")

    start = max(curve.starting_freq for curve in curves)
    end = min(curve.max_frequency for curve in curves)
    if start >= end:
        raise ValueError("Measurements do not have an overlapping frequency range")
    return start, end


def _build_deviation_curves(curves: List[Curve]):
    common_from, common_to = _get_common_frequency_range(curves)
    reference_from = max(REFERENCE_FROM, common_from)
    reference_to = min(REFERENCE_TO, common_to)
    if reference_from >= reference_to:
        raise ValueError(
            "Measurements do not have an overlapping reference range between "
            f"{REFERENCE_FROM} Hz and {REFERENCE_TO} Hz"
        )

    return [
        curve.to_deviation_curve(from_freq=reference_from, to_freq=reference_to)
        for curve in curves
    ]


def _validate_measurement_grids(curves: List[Curve], file_paths=None):
    curves = list(curves)
    if not curves:
        raise ValueError("At least one measurement is required")

    if file_paths is None:
        labels = [f"measurement {index + 1}" for index in range(len(curves))]
    else:
        labels = list(file_paths)

    reference = curves[0].domain_frequencies
    for index, curve in enumerate(curves[1:], start=1):
        frequencies = curve.domain_frequencies
        if len(frequencies) != len(reference):
            raise ValueError(
                "Measurement frequency grids differ: "
                f"{labels[0]!r} has {len(reference)} points, but "
                f"{labels[index]!r} has {len(frequencies)} points"
            )
        for point_index, (expected, actual) in enumerate(zip(reference, frequencies)):
            if actual != expected:
                raise ValueError(
                    "Measurement frequency grids differ: "
                    f"{labels[index]!r} has {actual:g} Hz at point {point_index + 1}, "
                    f"expected {expected:g} Hz from {labels[0]!r}"
                )
    return reference


def _validate_eq_points_in_range(eq_curve: Curve, eq_points):
    points = [float(point) for point in eq_points]
    lower_bound = eq_curve.starting_freq * (1 - EQ_POINT_RANGE_TOLERANCE)
    upper_bound = eq_curve.max_frequency * (1 + EQ_POINT_RANGE_TOLERANCE)
    out_of_range = [
        point for point in points
        if point < lower_bound or point > upper_bound
    ]
    if out_of_range:
        shown = ", ".join("%.1f" % point for point in out_of_range[:5])
        if len(out_of_range) > 5:
            shown += ", ..."
        raise ValueError(
            "EQ points fall outside the measured frequency range "
            f"{eq_curve.starting_freq:.1f}-{eq_curve.max_frequency:.1f} Hz: {shown}"
        )
    return points


def calc_eq_curve(measurements: List[Measurement], target_curve: Curve, eq_config: EQConfig.EQConfig):
    """
    Calculates a Graphic Equalizer for multiple measurement and a target curve
    :param eq_config: configuration for the eq generation
    :param measurements: List of deviation curves
    :param target_curve: A curve that represents the eq target
    :return: EQ curve on the measurements' native frequency grid
    """
    if not measurements:
        raise ValueError("At least one measurement is required")

    curves = [measurement.curve for measurement in measurements]
    eq_points = _validate_measurement_grids(curves)
    eq_from, eq_to = eq_points[0], eq_points[-1]
    eq_level = []

    for hz_value in eq_points:
        eq_level.append(
            calc_boost(
                measurements,
                hz_value,
                target_curve(hz_value),
                eq_config,
                frequency_range=(eq_from, eq_to),
            )
        )
    return Curve(eq_points, eq_level)


def _estimate_avg_err(target: Curve, estimated_response: Curve, start, verbose=False):
    errs = []
    for point in estimated_response.domain_frequencies:
        errs.append(abs(target(point) - estimated_response(point)))

    med = round(Utils.median(errs), 1)
    if verbose:
        print(start + " deviates ",
              med,
              " dB on average from the target")
    return med


def create_eq(
        measurements_dir: str = None,
        file_paths: List[str] = None,
        eq_config=None,
        target_curve=None,
        draw=False,
        verbose=False,
):
    if eq_config is None:
        eq_config = EQConfig.EQConfig()
    if target_curve is None:
        target_curve = TargetCurves.linear()

    file_paths = get_files(dir_path=measurements_dir, file_paths=file_paths)
    raw_curves = [curve_from_rew_file(file_path) for file_path in file_paths]
    _validate_measurement_grids(raw_curves, file_paths=file_paths)
    curves = _build_deviation_curves(raw_curves)

    avg = Curve.build_average_curve(curves)
    if draw:
        avg.smooth(SmoothingFactor.LIGHT_SMOOTHING).draw("Averaged Frequency Response of all Measurements")
    _estimate_avg_err(target_curve, avg, "The current fr", verbose=verbose)

    measurements = list(map(Measurement, curves))

    target_curve = TargetCurves.adjust_bass_target(target_curve, measurements)
    if draw:
        target_curve.draw("Target Curve")
    eq_curve = calc_eq_curve(measurements, target_curve, eq_config)
    estimated_fr = eq_curve + avg
    estimated_fr = estimated_fr.smooth(SmoothingFactor.LIGHT_SMOOTHING)
    if draw:
        estimated_fr.draw("Estimated Frequency Response after Equalization")

    _estimate_avg_err(target_curve, estimated_fr, "The estimated", verbose=verbose)

    return eq_curve


def format_eq_str(eq_curve: Curve, config=None):
    if config is None:
        config = EQConfig.default()

    eq_points = _validate_eq_points_in_range(eq_curve, config.eq_points)
    level_adjustments = [float(level) for level in eq_curve(eq_points)]

    if config.set_max_zero:
        max_boost = max(level_adjustments)
        level_adjustments = [l - max_boost for l in level_adjustments]
    else:
        level_adjustments = [min(level, config.max_boost) for level in level_adjustments]

    str_adjustments = ['%.1f' % level for level in level_adjustments]
    eq_points = map(lambda point: "%g" % point, eq_points)

    freq_boost_tuples = zip(eq_points, str_adjustments)
    combo = map(" ".join, freq_boost_tuples)

    return "GraphicEQ: " + "; ".join(combo)


def get_graph_eq_str(
        measurements_dir: str = None,
        file_paths: List[str] = None,
        eq_config=None,
        target_curve=None,
        draw=False,
        verbose=False):
    if eq_config is None:
        eq_config = EQConfig.default()
    if target_curve is None:
        target_curve = TargetCurves.linear()

    eq = create_eq(
        measurements_dir=measurements_dir,
        file_paths=file_paths,
        eq_config=eq_config,
        target_curve=target_curve,
        draw=draw,
        verbose=verbose,
    )
    return format_eq_str(eq, config=eq_config)
