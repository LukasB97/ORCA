import unittest

from orca import TargetCurves, WeightingFuns
from orca.BoostComputation import minimize
from orca.Curve import Curve
from orca.EQConfig import EQConfig
from orca.Measurement import Measurement
from orca.RewToGraphEq import calc_eq_curve


def _config_for_synthetic_tests():
    return EQConfig(
        eq_points=[100, 1000, 10000],
        set_max_zero=False,
        weighting_fun=WeightingFuns.no_smoothing(),
    )


class SyntheticCurveTests(unittest.TestCase):
    def test_flat_measurement_needs_no_eq(self):
        measurement = Measurement(Curve([100, 1000, 10000], [0, 0, 0]))

        eq = calc_eq_curve(
            [measurement],
            TargetCurves.linear(),
            _config_for_synthetic_tests(),
            res=3,
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
            res=3,
        )

        self.assertLess(float(eq(1000)), -1)

    def test_dip_is_corrected_upward(self):
        measurement = Measurement(Curve([100, 1000, 10000], [0, -10, 0]))

        eq = calc_eq_curve(
            [measurement],
            TargetCurves.linear(),
            _config_for_synthetic_tests(),
            res=3,
        )

        self.assertGreater(float(eq(1000)), 1)

    def test_multiple_measurements_average_the_needed_correction(self):
        lower = Measurement(Curve([100, 1000, 10000], [0, -6, 0]))
        higher = Measurement(Curve([100, 1000, 10000], [0, 6, 0]))

        eq = calc_eq_curve(
            [lower, higher],
            TargetCurves.linear(),
            _config_for_synthetic_tests(),
            res=3,
        )

        self.assertAlmostEqual(float(eq(1000)), 0, delta=1)

    def test_measurement_order_does_not_change_frequency_weighting(self):
        wide = Measurement(Curve([20, 20000], [10, 10]))
        narrow = Measurement(Curve([100, 10000], [10, 10]))
        config = EQConfig(
            eq_points=[100, 1000, 10000],
            set_max_zero=False,
            weighting_fun=lambda iteration, pos: pos,
        )

        wide_first = calc_eq_curve(
            [wide, narrow], TargetCurves.linear(), config, res=3
        )
        narrow_first = calc_eq_curve(
            [narrow, wide], TargetCurves.linear(), config, res=3
        )

        for frequency in (100, 1000, 10000):
            self.assertAlmostEqual(
                float(wide_first(frequency)),
                float(narrow_first(frequency)),
                places=6,
            )

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
