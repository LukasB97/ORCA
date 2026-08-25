import unittest

import numpy as np

from orca import TargetCurves, WeightingFuns
from orca.BoostComputation import minimize
from orca.Curve import Curve
from orca.EQConfig import EQConfig
from orca.Measurement import Measurement
from orca.RewToGraphEq import _build_interpolation_matrix, calc_eq_curve
from orca.Smoothing import SmoothingFactor


def _config_for_synthetic_tests():
    return EQConfig(
        eq_points=[100, 1000, 10000],
        set_max_zero=False,
        weighting_fun=WeightingFuns.no_smoothing(),
    )


class SyntheticCurveTests(unittest.TestCase):
    def test_graphic_eq_interpolation_uses_log_frequency(self):
        interpolation = _build_interpolation_matrix(
            [100, 800],
            [100, 200, 400, 800],
        )

        np.testing.assert_allclose(
            interpolation,
            [
                [1, 0],
                [2 / 3, 1 / 3],
                [1 / 3, 2 / 3],
                [0, 1],
            ],
        )

    def test_flat_measurement_needs_no_eq(self):
        measurement = Measurement(Curve([100, 1000, 10000], [0, 0, 0]))

        eq = calc_eq_curve(
            [measurement],
            TargetCurves.linear(),
            _config_for_synthetic_tests(),
        )

        self.assertAlmostEqual(float(eq(100)), 0, delta=0.1)
        self.assertAlmostEqual(float(eq(1000)), 0, delta=0.1)
        self.assertAlmostEqual(float(eq(10000)), 0, delta=0.1)

    def test_peak_is_corrected_downward(self):
        measurement = Measurement(Curve([100, 1000, 10000], [0, 10, 0]))

        eq = calc_eq_curve(
            [measurement],
            TargetCurves.linear(),
            _config_for_synthetic_tests(),
        )

        self.assertLess(float(eq(1000)), -1)

    def test_dip_is_corrected_upward(self):
        measurement = Measurement(Curve([100, 1000, 10000], [0, -10, 0]))

        eq = calc_eq_curve(
            [measurement],
            TargetCurves.linear(),
            _config_for_synthetic_tests(),
        )

        self.assertGreater(float(eq(1000)), 1)

    def test_multiple_measurements_average_the_needed_correction(self):
        lower = Measurement(Curve([100, 1000, 10000], [0, -6, 0]))
        higher = Measurement(Curve([100, 1000, 10000], [0, 6, 0]))

        eq = calc_eq_curve(
            [lower, higher],
            TargetCurves.linear(),
            _config_for_synthetic_tests(),
        )

        self.assertAlmostEqual(float(eq(1000)), 0, delta=1)

    def test_eq_optimizes_only_configured_control_points(self):
        frequencies = [100, 200, 400, 800]
        measurement = Measurement(Curve(frequencies, [0, 10, 0, 0]))
        config = EQConfig(
            eq_points=[100, 800],
            set_max_zero=False,
            weighting_fun=WeightingFuns.no_smoothing(),
        )

        eq = calc_eq_curve(
            [measurement],
            TargetCurves.linear(),
            config,
        )
        corrected_peak = measurement.curve(200) + eq(200)

        self.assertEqual(eq.domain_frequencies, [100, 800])
        self.assertLess(float(corrected_peak), 10)

    def test_octave_smoothing_is_independent_of_measurement_density(self):
        def build_curve(points_per_octave):
            frequencies = np.logspace(
                np.log2(100),
                np.log2(10000),
                round(np.log2(10000 / 100) * points_per_octave) + 1,
                base=2,
            )
            levels = 10 * np.exp(-0.5 * (np.log2(frequencies / 1000) / 0.08) ** 2)
            return Curve(frequencies, levels)

        coarse = build_curve(48).smooth(SmoothingFactor.DEFAULT_SMOOTHING)
        dense = build_curve(96).smooth(SmoothingFactor.DEFAULT_SMOOTHING)

        self.assertAlmostEqual(float(coarse(1000)), float(dense(1000)), delta=0.03)

    def test_smoothing_rejects_non_logarithmic_frequency_grid(self):
        curve = Curve([100, 200, 1000], [0, 1, 0])

        with self.assertRaisesRegex(ValueError, "logarithmically uniform"):
            curve.smooth(SmoothingFactor.DEFAULT_SMOOTHING)

    def test_deviation_curve_uses_midband_reference_not_full_range(self):
        bass_heavy = Curve([20, 100, 1000, 10000], [20, 0, 0, 0])

        deviation = bass_heavy.to_deviation_curve()

        self.assertAlmostEqual(float(deviation(1000)), 0, delta=0.1)
        self.assertGreater(float(deviation(20)), 15)

    def test_minimize_handles_peak_and_dip_direction(self):
        self.assertAlmostEqual(minimize(0, [6]), -6, delta=0.1)
        self.assertAlmostEqual(minimize(0, [-6]), 6, delta=0.1)


if __name__ == "__main__":
    unittest.main()
