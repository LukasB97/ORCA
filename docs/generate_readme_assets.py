"""Generate versioned README graphics from ORCA's example measurements."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orca import TargetCurves, build_export_curve, create_eq, wavelet_config  # noqa: E402
from orca.Curve import Curve  # noqa: E402
from orca.FileReader import curve_from_rew_file  # noqa: E402
from orca.Measurement import Measurement  # noqa: E402
from orca.Smoothing import SmoothingFactor  # noqa: E402

REFERENCE_RANGE = (100.0, 10_000.0)
MEASUREMENTS_DIR = ROOT / "example measurements"
OUTPUT = ROOT / "docs" / "assets" / "orca-readme-overview.png"


def _align_to_target(curve: Curve, target: Curve) -> Curve:
    reference_points = [
        frequency
        for frequency in curve.domain_frequencies
        if REFERENCE_RANGE[0] <= frequency <= REFERENCE_RANGE[1]
    ]
    offset = float(
        np.mean(np.asarray(target(reference_points)) - np.asarray(curve(reference_points)))
    )
    return Curve(
        curve.domain_frequencies,
        [value + offset for value in curve.domain_values],
    )


def _mean_absolute_deviation(curve: Curve, target: Curve) -> float:
    points = curve.domain_frequencies
    return float(np.mean(np.abs(np.asarray(curve(points)) - np.asarray(target(points)))))


def main() -> None:
    try:
        from matplotlib import pyplot
        from matplotlib.ticker import FuncFormatter
    except ImportError as exc:
        raise SystemExit(
            "Install plotting support with `python -m pip install -e .[plot]`."
        ) from exc

    measurement_paths = sorted(MEASUREMENTS_DIR.glob("*.txt"))
    raw_curves = [curve_from_rew_file(path) for path in measurement_paths]
    deviation_curves = [curve.to_deviation_curve(*REFERENCE_RANGE) for curve in raw_curves]
    average = Curve.build_average_curve(deviation_curves)

    measurements = [Measurement(curve) for curve in deviation_curves]
    target = TargetCurves.adjust_bass_target(TargetCurves.linear(), measurements)
    config = wavelet_config()
    equalizer = create_eq(
        measurements_dir=str(MEASUREMENTS_DIR),
        eq_config=config,
        reference_range=REFERENCE_RANGE,
    )
    exported_equalizer = build_export_curve(equalizer, config)
    estimated = average + Curve(
        average.domain_frequencies,
        exported_equalizer(average.domain_frequencies),
    )

    aligned_average = _align_to_target(average, target)
    aligned_estimated = _align_to_target(estimated, target)
    display_average = aligned_average.smooth(SmoothingFactor.LIGHT_SMOOTHING)
    display_estimated = aligned_estimated.smooth(SmoothingFactor.LIGHT_SMOOTHING)

    before_error = _mean_absolute_deviation(aligned_average, target)
    after_error = _mean_absolute_deviation(aligned_estimated, target)
    frequencies = display_average.domain_frequencies

    pyplot.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.labelcolor": "#475569",
            "text.color": "#0f172a",
            "xtick.color": "#64748b",
            "ytick.color": "#64748b",
        }
    )
    figure, (response_axis, eq_axis) = pyplot.subplots(
        2,
        1,
        figsize=(10, 5.5),
        dpi=160,
        gridspec_kw={"height_ratios": (2.2, 1), "hspace": 0.32},
    )
    figure.patch.set_facecolor("white")
    figure.subplots_adjust(top=0.94, bottom=0.11, left=0.085, right=0.98)

    response_axis.plot(
        frequencies,
        display_average(frequencies),
        color="#94a3b8",
        linewidth=2,
        label=f"Before ORCA  ·  {before_error:.1f} dB mean error",
    )
    response_axis.plot(
        frequencies,
        target(frequencies),
        color="#f59e0b",
        linewidth=1.8,
        linestyle=(0, (5, 4)),
        label="Bass-aware target",
    )
    response_axis.plot(
        frequencies,
        display_estimated(frequencies),
        color="#0284c7",
        linewidth=2.4,
        label=f"Estimated after ORCA  ·  {after_error:.1f} dB mean error",
    )
    response_axis.set_title("Estimated in-room frequency response", loc="left", fontsize=12)
    response_axis.set_ylabel("Relative level (dB)")
    response_axis.legend(loc="lower right", frameon=False, fontsize=9)

    eq_frequencies = exported_equalizer.domain_frequencies
    eq_levels = exported_equalizer.domain_values
    eq_axis.plot(eq_frequencies, eq_levels, color="#6366f1", linewidth=2)
    eq_axis.fill_between(eq_frequencies, eq_levels, 0, color="#c7d2fe", alpha=0.65)
    eq_axis.axhline(0, color="#64748b", linewidth=1)
    eq_axis.set_title("Generated Wavelet GraphicEQ", loc="left", fontsize=12)
    eq_axis.set_xlabel("Frequency (Hz)")
    eq_axis.set_ylabel("Gain (dB)")

    def format_frequency(value: float, _position: float) -> str:
        if value >= 1000:
            return f"{value / 1000:g}k"
        return f"{value:g}"

    for axis in (response_axis, eq_axis):
        axis.set_xscale("log")
        axis.set_xlim(20, 20_000)
        axis.set_xticks([20, 50, 100, 200, 500, 1000, 2000, 5000, 10_000, 20_000])
        axis.xaxis.set_major_formatter(FuncFormatter(format_frequency))
        axis.grid(True, which="major", color="#e2e8f0", linewidth=0.8)
        axis.grid(False, which="minor")
        for side in ("top", "right"):
            axis.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            axis.spines[side].set_color("#cbd5e1")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT, bbox_inches="tight", facecolor="white")
    pyplot.close(figure)
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
