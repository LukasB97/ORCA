from typing import List

import Utils
from BoostComputation import calc_boost
from Curve import Curve
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

def _get_avg(measurements: List[Measurement]):
    curves = [c.curve.smooth(SmoothingFactor.LIGHT_SMOOTHING) for c in measurements]
    fc = measurements[0].curve
    y = []
    for x in fc.x:
        y.append(Utils.avg([f.log_eval(x) for f in curves]))
    return Curve(fc.x, y, log_base=fc.log_base, starting_freq=fc.starting_freq)


def _draw_equalized(avg, eq):
    (avg + eq).draw()




def create_eq(
        measurements_dir: str = None,
        file_paths: List[str] = None,
        eq_config=EQConfig.EQConfig(),
        target_curve=TargetCurves.linear()
):
    file_paths = get_files(dir_path=measurements_dir, file_paths=file_paths)

    measurements: List[Measurement] = list(
        map(Measurement,
            map(Curve.to_deviation_curve, map(curve_from_rew_file, file_paths))
            )
    )
    avg = _get_avg(measurements)
    avg.draw()

    target_curve = TargetCurves.adjust_bass_target(target_curve, measurements)
    eq_curve = calc_eq_curve(measurements, target_curve, eq_config)
    eqed_curve = avg + eq_curve
    err = 0
    for point in eq_config.eq_points:
        err += (target_curve(point) - eqed_curve(point)) ** 2


    print(err)
    _draw_equalized(avg, eq_curve)
    return eq_curve


def get_graph_eq_str(
        measurements_dir: str = None,
        file_paths: List[str] = None,
        eq_config=EQConfig.default,
        target_curve=TargetCurves.linear()):
    eq = create_eq(measurements_dir, file_paths, eq_config, target_curve)
    return eq_config.format(eq)

