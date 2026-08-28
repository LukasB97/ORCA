from __future__ import annotations

import unittest

import numpy as np

from orca import TargetCurves
from orca.Curve import Curve
from orca.Measurement import Measurement
from orca.TargetCurves import _boost_multiplier, _first_target_crossing


class BassTargetTests(unittest.TestCase):
    def test_first_crossing_is_interpolated_against_non_flat_target(self) -> None:
        frequencies = np.asarray([20.0, 40.0, 80.0, 160.0])
        deviations = np.asarray([-8.0, -2.0, 2.0, 3.0])

        crossing = _first_target_crossing(frequencies, deviations, upper_bound=200.0)

        self.assertIsNotNone(crossing)
        self.assertAlmostEqual(float(crossing), 56.5685, places=3)

    def test_boost_multiplier_preserves_small_deficits_and_rejects_deep_bass(self) -> None:
        self.assertEqual(_boost_multiplier(5.0), 1.0)
        self.assertAlmostEqual(_boost_multiplier(15.0), 0.5, delta=0.02)
        self.assertLess(_boost_multiplier(35.0), 1e-8)

    def test_adjusted_target_uses_cubic_extension_without_deep_bass_boost(self) -> None:
        frequencies = np.geomspace(20.0, 2_000.0, 240)
        target = Curve(frequencies, np.zeros_like(frequencies))
        measured_levels = np.interp(
            np.log2(frequencies),
            np.log2([20.0, 30.0, 40.0, 50.0, 55.0, 80.0, 2_000.0]),
            [-35.0, -36.0, -35.0, -5.0, 1.0, 2.0, 2.0],
        )
        measurement = Measurement(Curve(frequencies, measured_levels))

        adjusted = TargetCurves.adjust_bass_target(target, [measurement], max_boost=5.0)

        self.assertLess(adjusted(20.0), -30.0)
        self.assertGreater(adjusted(52.0), -8.0)
        self.assertAlmostEqual(adjusted(70.0), 0.0, places=6)
        self.assertTrue(all(level <= 0.0 for level in adjusted.domain_values))

    def test_adjusted_target_follows_a_non_flat_target_after_crossing(self) -> None:
        frequencies = np.geomspace(20.0, 2_000.0, 240)
        target = Curve([20.0, 200.0, 2_000.0], [3.0, 0.0, -2.0])
        target_levels = np.asarray(target(frequencies))
        relative = np.log2(frequencies / 80.0)
        deviations = np.where(frequencies < 80.0, 8.0 * relative, 2.0)
        measurement = Measurement(Curve(frequencies, target_levels + deviations))

        adjusted = TargetCurves.adjust_bass_target(target, [measurement], max_boost=5.0)

        self.assertAlmostEqual(adjusted(120.0), target(120.0), places=6)
        self.assertTrue(
            all(adjusted(frequency) <= target(frequency) + 1e-9 for frequency in frequencies)
        )

    def test_target_is_unchanged_when_no_crossing_exists(self) -> None:
        frequencies = np.geomspace(20.0, 2_000.0, 120)
        target = Curve(frequencies, np.zeros_like(frequencies))
        measurement = Measurement(Curve(frequencies, np.full_like(frequencies, -10.0)))

        adjusted = TargetCurves.adjust_bass_target(target, [measurement])

        np.testing.assert_allclose(adjusted.domain_values, target.domain_values)


if __name__ == "__main__":
    unittest.main()
