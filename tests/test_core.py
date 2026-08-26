import contextlib
import importlib
import io
import math
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError, is_dataclass
from decimal import localcontext
from fractions import Fraction
from pathlib import Path
from unittest import mock

import orca
from examples import custom_eq_config_example
from orca.BoostComputation import minimize
from orca.cli import main
from orca.Curve import Curve, PlottingDependencyError
from orca.EQConfig import EQConfig
from orca.FileReader import curve_from_rew_file, get_files, read_hz_and_spl
from orca.RewToGraphEq import (
    _build_deviation_curves,
    _estimate_error_stats,
    _validate_measurement_grids,
    build_export_curve,
    create_eq,
    format_eq_str,
)
from orca.Utils import log_spaced_ints
from orca.Wavelet import WAVELET_POINTS
from orca.Wavelet import config as wavelet_config

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_MEASUREMENTS = ROOT / "example measurements"


class ImportAndCurveTests(unittest.TestCase):
    def test_package_exposes_stable_public_api(self):
        expected_api = {
            "TargetCurves",
            "build_export_curve",
            "create_eq",
            "format_eq_str",
            "get_graph_eq_str",
            "wavelet_config",
        }

        self.assertEqual(set(orca.__all__), expected_api)
        self.assertTrue(all(hasattr(orca, name) for name in expected_api))

    def test_public_api_does_not_shadow_legacy_submodules(self):
        curve_module = importlib.import_module("orca.Curve")
        config_module = importlib.import_module("orca.EQConfig")

        self.assertIs(orca.Curve, curve_module)
        self.assertIs(orca.EQConfig, config_module)
        self.assertIs(curve_module.Curve, Curve)
        self.assertIs(config_module.EQConfig, EQConfig)

    def test_curve_module_does_not_import_matplotlib(self):
        script = "import sys; import orca.RewToGraphEq; print('matplotlib' in sys.modules)"
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.stdout.strip(), "False")

    def test_curve_draw_reports_missing_plotting_dependency(self):
        curve = Curve([100, 1000], [0, 0])

        with mock.patch.dict(sys.modules, {"matplotlib": None}):
            with self.assertRaisesRegex(PlottingDependencyError, "requires matplotlib"):
                curve.draw()

    def test_curve_accepts_scalar_and_iterables(self):
        curve = Curve([10, 100], [0, 10])

        self.assertAlmostEqual(float(curve(10)), 0)
        self.assertEqual(len(curve([10, 100])), 2)
        self.assertEqual(len(curve(10, 100)), 2)

    def test_curve_preserves_original_frequency_grid(self):
        frequencies = [20, 30, 100, 1000]
        curve = Curve(frequencies, [0, 1, 2, 3])

        self.assertEqual(curve.domain_frequencies, frequencies)

    def test_curve_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            Curve([], [])
        with self.assertRaises(ValueError):
            Curve([0], [1])
        with self.assertRaises(ValueError):
            Curve([10, 20], [1])
        with self.assertRaises(ValueError):
            Curve([20, 10], [1, 2])
        with self.assertRaises(ValueError):
            Curve([20, float("nan")], [1, 2])
        with self.assertRaises(ValueError):
            Curve([20, 30], [1, float("inf")])

    def test_curve_rejects_invalid_eval_frequency(self):
        curve = Curve([10, 100], [0, 10])

        with self.assertRaises(ValueError):
            curve(0)

    def test_deviation_curve_uses_valid_reference_overlap(self):
        curve = Curve([200, 1000], [1, 2])

        deviation = curve.to_deviation_curve()

        self.assertGreaterEqual(deviation.starting_freq, 200)
        self.assertLessEqual(deviation.max_frequency, 1000)

    def test_deviation_curve_rejects_missing_reference_overlap(self):
        curve = Curve([20, 50], [1, 2])

        with self.assertRaisesRegex(ValueError, "Reference frequency range"):
            curve.to_deviation_curve()

    def test_curve_operations_reject_non_overlapping_domains(self):
        left = Curve([10, 20], [0, 1])
        right = Curve([30, 40], [0, 1])

        with self.assertRaisesRegex(ValueError, "overlapping"):
            left + right
        with self.assertRaisesRegex(ValueError, "overlapping"):
            Curve.build_average_curve([left, right])

    def test_curve_operations_merge_natural_frequency_grids(self):
        left = Curve([10, 20, 40, 100], [0, 0, 0, 0])
        right = Curve([20, 30, 100], [1, 1, 1])

        combined = left + right

        self.assertEqual(combined.domain_frequencies, [20, 30, 40, 100])

    def test_average_curve_uses_decibel_power_scale(self):
        quiet = Curve([100, 1000], [0, 0])
        loud = Curve([100, 1000], [10, 10])

        average = Curve.build_average_curve([quiet, loud])

        expected = 10 * math.log10((10 ** (0 / 10) + 10 ** (10 / 10)) / 2)
        self.assertAlmostEqual(float(average(100)), expected, places=6)


class FileReaderTests(unittest.TestCase):
    def test_rew_parser_handles_whitespace_and_extra_columns(self):
        content = """
* Header
* Freq(Hz) SPL(dB) Phase(degrees)
19.0 1.0 0
20.0    2.45    0
30.0\t3.51\t1\textra
"""
        frequencies, spl = read_hz_and_spl(content)

        self.assertEqual(frequencies, [19.0, 20.0, 30.0])
        self.assertEqual(spl, [1.0, 2.45, 3.51])

    def test_rew_parser_handles_decimal_commas(self):
        content = """
* Freq(Hz) SPL(dB) Phase(degrees)
20,0 2,45 0
30,0 3,51 0
"""
        frequencies, spl = read_hz_and_spl(content)

        self.assertEqual(frequencies, [20.0, 30.0])
        self.assertEqual(spl, [2.45, 3.51])

    def test_rew_file_reader_falls_back_to_cp1252(self):
        content = """
* Quelle: Gerät
* Freq(Hz) SPL(dB) Phase(degrees)
20.0 2.0 0
30.0 3.0 0
""".strip()

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "measurement.txt"
            file_path.write_bytes(content.encode("cp1252"))

            curve = curve_from_rew_file(file_path)

        self.assertEqual(float(curve(20)), 2.0)

    def test_rew_parser_rejects_missing_header(self):
        with self.assertRaisesRegex(ValueError, "header"):
            read_hz_and_spl("20.0 1.0 0")

    def test_rew_parser_preserves_frequencies_below_20_hz(self):
        content = """
        * Freq(Hz) SPL(dB) Phase(degrees)
        10.0 1.0 0
        19.0 2.0 0
        """

        frequencies, spl = read_hz_and_spl(content)

        self.assertEqual(frequencies, [10.0, 19.0])
        self.assertEqual(spl, [1.0, 2.0])

    def test_rew_parser_rejects_nonpositive_frequencies(self):
        content = """
        * Freq(Hz) SPL(dB) Phase(degrees)
        0.0 1.0 0
        """

        with self.assertRaisesRegex(ValueError, "Invalid REW data row"):
            read_hz_and_spl(content)

    def test_rew_parser_rejects_non_finite_rows(self):
        content = """
* Freq(Hz) SPL(dB) Phase(degrees)
20.0 nan 0
"""
        with self.assertRaisesRegex(ValueError, "Invalid REW data row"):
            read_hz_and_spl(content)

    def test_get_files_does_not_change_working_directory(self):
        before = Path.cwd()
        files = get_files(dir_path=str(EXAMPLE_MEASUREMENTS))

        self.assertEqual(Path.cwd(), before)
        self.assertEqual(len(files), 5)
        self.assertTrue(all(Path(file).suffix == ".txt" for file in files))

    def test_get_files_does_not_mutate_supplied_file_list(self):
        supplied_files = [str(EXAMPLE_MEASUREMENTS / "Sep 13.txt")]
        original_files = supplied_files.copy()

        get_files(dir_path=str(EXAMPLE_MEASUREMENTS), file_paths=supplied_files)

        self.assertEqual(supplied_files, original_files)

    def test_get_files_deduplicates_directory_and_explicit_inputs(self):
        measurement = EXAMPLE_MEASUREMENTS / "Sep 13.txt"

        files = get_files(
            dir_path=str(EXAMPLE_MEASUREMENTS),
            file_paths=[str(measurement)],
        )

        self.assertEqual(len(files), 5)
        self.assertEqual(
            len({str(Path(file).resolve()).lower() for file in files}),
            len(files),
        )

    def test_get_files_rejects_missing_inputs(self):
        with self.assertRaises(ValueError):
            get_files()
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                get_files(dir_path=temp_dir)


class ConfigAndEndToEndTests(unittest.TestCase):
    def test_eq_config_is_an_immutable_dataclass(self):
        config = EQConfig(eq_points=[100, 1000])

        self.assertTrue(is_dataclass(config))
        with self.assertRaises(FrozenInstanceError):
            config.max_boost = 5.0

    def test_eq_config_from_range_builds_requested_grid(self):
        config = EQConfig.from_range(eq_from=30, eq_to=18000, eq_res=256)

        self.assertEqual(len(config.eq_points), 256)
        self.assertEqual(config.eq_points[0], 30.0)
        self.assertEqual(config.eq_points[-1], 18000.0)

    def test_wavelet_config_uses_wavelet_frequency_layout(self):
        config = wavelet_config()

        self.assertEqual(config.eq_points, tuple(float(point) for point in WAVELET_POINTS))

    def test_log_spaced_int_error_is_informative(self):
        with self.assertRaisesRegex(ValueError, "Cannot create 128 ints"):
            log_spaced_ints(20, 30, count=128)

    def test_log_spaced_ints_include_exact_integer_bounds(self):
        points = log_spaced_ints(20, 30, count=11)

        self.assertEqual(points, list(range(20, 31)))

    def test_log_spaced_ints_do_not_truncate_float_artifacts(self):
        points = log_spaced_ints(30, 18000, count=256)

        self.assertEqual(len(points), 256)
        self.assertEqual(points[0], 30)
        self.assertEqual(points[-1], 18000)

    def test_minimize_rejects_empty_spl(self):
        with self.assertRaises(ValueError):
            minimize(0, [])

    def test_minimize_handles_identical_spl_values(self):
        self.assertEqual(minimize(0, [2, 2]), -2)

    def test_graph_eq_generation_from_examples(self):
        eq_config = EQConfig()
        eq_curve = create_eq(
            measurements_dir=str(EXAMPLE_MEASUREMENTS),
            eq_config=eq_config,
        )
        output = format_eq_str(eq_curve, eq_config)

        self.assertEqual(eq_curve.domain_frequencies, list(eq_config.eq_points))
        self.assertAlmostEqual(max(eq_curve.domain_values), 0.0, places=9)
        self.assertTrue(output.startswith("GraphicEQ: "))
        self.assertEqual(output.count(";") + 1, len(eq_config.eq_points))
        levels = {
            float(frequency): float(level)
            for frequency, level in (
                point.split() for point in output.removeprefix("GraphicEQ: ").split("; ")
            )
        }
        expected_levels = {
            20: -2.0,
            29: -0.8,
            1004: -4.5,
            9862: -4.8,
            20000: -2.5,
        }
        for frequency, expected in expected_levels.items():
            self.assertAlmostEqual(levels[frequency], expected, delta=0.2)

    def test_custom_eq_points_accept_iterables_and_are_immutable(self):
        config = EQConfig(eq_points=(point for point in [100, 1000, 10000]))

        self.assertEqual(config.eq_points, (100.0, 1000.0, 10000.0))

    def test_custom_eq_points_must_be_strictly_increasing(self):
        invalid_points = (
            [1000, 100],
            [100, 100, 1000],
        )

        for points in invalid_points:
            with self.subTest(points=points):
                with self.assertRaisesRegex(ValueError, "strictly increasing"):
                    EQConfig(eq_points=points)

    def test_custom_eq_points_must_be_finite_and_positive(self):
        invalid_points = (
            [0, 100],
            [100, float("inf")],
            [100, float("nan")],
        )

        for points in invalid_points:
            with self.subTest(points=points):
                with self.assertRaisesRegex(ValueError, "finite frequencies"):
                    EQConfig(eq_points=points)

    def test_eq_config_rejects_invalid_output_options(self):
        invalid_options = (
            {"set_max_zero": 1},
            {"max_boost": float("nan")},
            {"max_boost": 0.05},
            {"weighting_fun": None},
        )

        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    EQConfig(**options)

    def test_max_boost_validation_is_decimal_context_independent(self):
        with localcontext() as context:
            context.prec = 2
            config = EQConfig()

        self.assertEqual(config.max_boost, 10.0)

    def test_max_boost_accepts_large_integers(self):
        config = EQConfig(max_boost=10**27)

        self.assertEqual(config.max_boost, float(10**27))

    def test_max_boost_accepts_real_number_implementations(self):
        config = EQConfig(max_boost=Fraction(1, 10))

        self.assertEqual(config.max_boost, 0.1)

    def test_custom_eq_config_example_runs_with_bundled_measurements(self):
        output = custom_eq_config_example()

        self.assertTrue(output.startswith("GraphicEQ: "))

    def test_format_eq_rejects_points_far_outside_curve_domain(self):
        curve = Curve([100, 10000], [0, 0])
        config = EQConfig(eq_points=[20, 100, 10000, 20000])

        with self.assertRaisesRegex(ValueError, "outside the measured frequency range"):
            format_eq_str(curve, config)

    def test_format_eq_allows_small_rew_endpoint_rounding(self):
        curve = Curve([20.1, 19897], [0, 0])
        config = EQConfig(eq_points=[20, 1000, 20000])

        output = format_eq_str(curve, config)

        self.assertTrue(output.startswith("GraphicEQ: "))

    def test_format_eq_preserves_shape_when_anchoring_at_zero(self):
        curve = Curve([100, 1000], [11, 20])
        config = EQConfig(
            eq_points=[100, 1000],
            max_boost=10,
            set_max_zero=True,
        )

        self.assertEqual(format_eq_str(curve, config), "GraphicEQ: 100 -9.0; 1000 0.0")

    def test_format_eq_caps_boost_without_zero_anchor(self):
        curve = Curve([100, 1000], [11, 20])
        config = EQConfig(
            eq_points=[100, 1000],
            max_boost=10,
            set_max_zero=False,
        )

        self.assertEqual(format_eq_str(curve, config), "GraphicEQ: 100 10.0; 1000 10.0")

    def test_format_eq_respects_single_decimal_max_boost(self):
        curve = Curve([100, 1000], [0.06, 0.14])
        config = EQConfig(
            eq_points=[100, 1000],
            max_boost=0.1,
            set_max_zero=False,
        )

        self.assertEqual(format_eq_str(curve, config), "GraphicEQ: 100 0.1; 1000 0.1")

    def test_format_eq_without_config_preserves_existing_points_and_values(self):
        curve = Curve([100, 1000, 10000], [11, 20, -1])

        exported = build_export_curve(curve)

        self.assertEqual(exported.domain_frequencies, [100, 1000, 10000])
        self.assertEqual(exported.domain_values, [11, 20, -1])
        self.assertEqual(
            format_eq_str(curve),
            "GraphicEQ: 100 11.0; 1000 20.0; 10000 -1.0",
        )

    def test_format_created_custom_eq_without_config_keeps_custom_grid(self):
        config = EQConfig(eq_points=[20, 1000, 20000])
        curve = create_eq(
            measurements_dir=str(EXAMPLE_MEASUREMENTS),
            eq_config=config,
        )

        output = format_eq_str(curve)
        frequencies = [
            float(point.split()[0]) for point in output.removeprefix("GraphicEQ: ").split("; ")
        ]

        self.assertEqual(frequencies, list(config.eq_points))

    def test_export_curve_is_the_curve_serialized_by_formatter(self):
        curve = Curve([100, 200, 1000], [0, 20, 0])
        config = EQConfig(
            eq_points=[100, 1000],
            set_max_zero=False,
            max_boost=10,
        )

        exported = build_export_curve(curve, config)

        self.assertEqual(exported.domain_frequencies, [100, 1000])
        self.assertEqual(exported.domain_values, [0, 0])
        self.assertEqual(format_eq_str(curve, config), "GraphicEQ: 100 0.0; 1000 0.0")

    def test_error_stats_report_mean_and_95th_percentile(self):
        target = Curve([100, 10000], [0, 0])
        response = Curve([100, 1000, 10000], [0, 0, 100])

        mean, percentile_95 = _estimate_error_stats(
            target,
            response,
            "Response",
        )

        self.assertEqual(mean, 33.3)
        self.assertEqual(percentile_95, 90.0)

    def test_error_stats_can_ignore_overall_playback_level(self):
        target = Curve([100, 1000, 10000], [0, 0, 0])
        response = Curve([100, 1000, 10000], [-10, -10, -10])

        mean, percentile_95 = _estimate_error_stats(
            target,
            response,
            "Response",
            align_level=True,
        )

        self.assertEqual((mean, percentile_95), (0.0, 0.0))

    def test_measurements_need_reference_range_overlap(self):
        with self.assertRaisesRegex(ValueError, "reference range"):
            _build_deviation_curves(
                [
                    Curve([20, 50], [0, 1]),
                    Curve([20, 50], [1, 2]),
                ]
            )

    def test_measurements_require_same_frequency_count(self):
        with self.assertRaisesRegex(ValueError, "frequency grids differ"):
            _validate_measurement_grids(
                [
                    Curve([20, 100, 1000], [0, 0, 0]),
                    Curve([20, 100], [0, 0]),
                ]
            )

    def test_measurements_require_identical_frequency_values(self):
        with self.assertRaisesRegex(ValueError, "second.*expected 100 Hz"):
            _validate_measurement_grids(
                [
                    Curve([20, 100, 1000], [0, 0, 0]),
                    Curve([20, 101, 1000], [0, 0, 0]),
                ],
                file_paths=["first.txt", "second.txt"],
            )

    def test_cli_rejects_missing_input(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main([])

    def test_cli_reports_expected_input_errors_without_traceback(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as exit_context:
                main(["--measurements-dir", str(ROOT / "missing-measurements")])

        self.assertEqual(exit_context.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Measurement directory does not exist", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_reports_missing_plotting_dependency_without_traceback(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        plotting_error = PlottingDependencyError(
            "Plotting requires matplotlib. Install it with `pip install .[plot]`."
        )

        with mock.patch("orca.cli.get_graph_eq_str", side_effect=plotting_error):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exit_context:
                    main(["--file", "measurement.txt", "--draw"])

        self.assertEqual(exit_context.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("requires matplotlib", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_verbose_keeps_stdout_machine_readable(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            main(
                [
                    "--measurements-dir",
                    str(EXAMPLE_MEASUREMENTS),
                    "--verbose",
                ]
            )

        self.assertTrue(stdout.getvalue().startswith("GraphicEQ: "))
        self.assertEqual(len(stdout.getvalue().strip().splitlines()), 1)
        self.assertIn("Current frequency response", stderr.getvalue())
        self.assertIn("Estimated equalized response", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
