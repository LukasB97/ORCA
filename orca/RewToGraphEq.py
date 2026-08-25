import math
from typing import List

import numpy as np

from . import TargetCurves, EQConfig
from .BoostComputation import minimize
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


def _build_interpolation_matrix(control_points, evaluation_points):
    """Map GraphicEQ control-point gains to a logarithmic evaluation grid."""
    control_points = np.asarray(control_points, dtype=float)
    evaluation_points = np.asarray(evaluation_points, dtype=float)
    log_controls = np.log2(control_points)
    log_evaluations = np.log2(evaluation_points)
    matrix = np.zeros((len(evaluation_points), len(control_points)))

    for row, value in enumerate(log_evaluations):
        if value <= log_controls[0]:
            matrix[row, 0] = 1.0
            continue
        if value >= log_controls[-1]:
            matrix[row, -1] = 1.0
            continue

        right = int(np.searchsorted(log_controls, value, side="right"))
        left = right - 1
        width = log_controls[right] - log_controls[left]
        right_weight = (value - log_controls[left]) / width
        matrix[row, left] = 1.0 - right_weight
        matrix[row, right] = right_weight

    return matrix


def _apply_output_constraints(levels, config):
    levels = np.asarray(levels, dtype=float)
    if config.set_max_zero:
        return levels - np.max(levels)
    return np.minimum(levels, config.max_boost)


def calc_eq_curve(measurements: List[Measurement], target_curve: Curve, eq_config: EQConfig.EQConfig):
    """
    Calculates a Graphic Equalizer for multiple measurements and a target curve.

    The exported GraphicEQ point gains are optimized directly. Their interpolated
    response is evaluated on every point of the measurements' native frequency grid.

    :param eq_config: configuration for the eq generation
    :param measurements: List of deviation curves
    :param target_curve: A curve that represents the eq target
    :return: EQ curve on the configured GraphicEQ point grid
    """
    if not measurements:
        raise ValueError("At least one measurement is required")

    curves = [measurement.curve for measurement in measurements]
    measurement_points = _validate_measurement_grids(curves)
    eq_points = _validate_eq_points_in_range(curves[0], eq_config.eq_points)
    interpolation = _build_interpolation_matrix(eq_points, measurement_points)
    target_levels = np.asarray(target_curve(measurement_points), dtype=float)
    normalized_positions = (
        (np.log(measurement_points) - math.log(measurement_points[0]))
        / (math.log(measurement_points[-1]) - math.log(measurement_points[0]))
    )
    point_levels = np.zeros(len(eq_points), dtype=float)
    reference_mask = (
        (np.asarray(measurement_points) >= REFERENCE_FROM)
        & (np.asarray(measurement_points) <= REFERENCE_TO)
    )

    for iteration, smoothing_factor in enumerate(SmoothingFactor):
        current_boost = interpolation @ point_levels
        measurement_levels = np.asarray([
            measurement.eval(measurement_points, smoothing_factor)
            for measurement in measurements
        ], dtype=float)
        iteration_targets = target_levels
        if eq_config.set_max_zero:
            target_offset = np.mean(
                measurement_levels[:, reference_mask]
                + current_boost[reference_mask]
                - target_levels[reference_mask]
            )
            iteration_targets = target_levels + target_offset
        desired_updates = []
        for index, target_level in enumerate(iteration_targets):
            adjustment = minimize(
                target_level,
                list(measurement_levels[:, index] + current_boost[index]),
            )
            weight = eq_config.weighting_fun(
                iteration,
                float(normalized_positions[index]),
            )
            if not math.isfinite(weight):
                raise ValueError("weighting_fun must return finite values")
            desired_updates.append(adjustment * weight)

        point_update, *_ = np.linalg.lstsq(
            interpolation,
            np.asarray(desired_updates),
            rcond=None,
        )
        point_levels = _apply_output_constraints(point_levels + point_update, eq_config)

    return Curve(eq_points, point_levels)


def _estimate_error_stats(
        target: Curve,
        estimated_response: Curve,
        label,
        verbose=False,
        align_level=False,
):
    response_offset = 0.0
    if align_level:
        reference_points = [
            point for point in estimated_response.domain_frequencies
            if REFERENCE_FROM <= point <= REFERENCE_TO
        ]
        if not reference_points:
            raise ValueError("Error statistics require points in the reference range")
        response_offset = float(np.mean(
            np.asarray(target(reference_points))
            - np.asarray(estimated_response(reference_points))
        ))

    errs = []
    for point in estimated_response.domain_frequencies:
        errs.append(abs(target(point) - estimated_response(point) - response_offset))

    mean = round(float(np.mean(errs)), 1)
    percentile_95 = round(float(np.percentile(errs, 95)), 1)
    if verbose:
        alignment = " level-aligned" if align_level else ""
        print(
            f"{label}{alignment} mean absolute deviation from target: {mean:.1f} dB; "
            f"95th percentile: {percentile_95:.1f} dB"
        )
    return mean, percentile_95


def build_export_curve(eq_curve: Curve, config=None):
    """Return the exact point curve that is serialized as GraphicEQ."""
    if config is None:
        config = EQConfig.default()

    eq_points = _validate_eq_points_in_range(eq_curve, config.eq_points)
    level_adjustments = [float(level) for level in eq_curve(eq_points)]

    level_adjustments = _apply_output_constraints(level_adjustments, config)

    return Curve(eq_points, level_adjustments)


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
    _estimate_error_stats(
        target_curve,
        avg,
        "Current frequency response",
        verbose=verbose,
        align_level=True,
    )

    measurements = list(map(Measurement, curves))

    target_curve = TargetCurves.adjust_bass_target(target_curve, measurements)
    if draw:
        target_curve.draw("Target Curve")
    eq_curve = calc_eq_curve(measurements, target_curve, eq_config)
    export_curve = build_export_curve(eq_curve, eq_config)
    estimated_eq = Curve(
        avg.domain_frequencies,
        export_curve(avg.domain_frequencies),
    )
    estimated_fr = estimated_eq + avg
    if draw:
        estimated_fr.smooth(SmoothingFactor.LIGHT_SMOOTHING).draw(
            "Estimated Frequency Response after Equalization"
        )

    _estimate_error_stats(
        target_curve,
        estimated_fr,
        "Estimated equalized response",
        verbose=verbose,
        align_level=eq_config.set_max_zero,
    )

    return eq_curve


def format_eq_str(eq_curve: Curve, config=None):
    export_curve = build_export_curve(eq_curve, config)
    str_adjustments = ['%.1f' % level for level in export_curve.domain_values]
    eq_points = map(lambda point: "%g" % point, export_curve.domain_frequencies)

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
