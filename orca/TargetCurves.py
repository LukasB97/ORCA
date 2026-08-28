from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from os import PathLike
from pathlib import Path
from typing import SupportsFloat

from . import Smoothing
from .Curve import Curve
from .Measurement import Measurement
from .Utils import log_spaced

_TARGET_FROM_HZ = 1.0
_TARGET_TO_HZ = 25_000.0
_TARGET_RESOLUTION = 512


def _create_target_curve(
    freq_to_level: Mapping[float, float],
    interpolation_alg: str = "linear",
) -> Curve:
    if interpolation_alg != "linear" and len(freq_to_level) < 4:
        raise ValueError("Non-linear target curves require at least four points")

    frequencies = list(freq_to_level.keys())
    frequencies.sort()
    boost = []
    for freq in frequencies:
        boost.append(freq_to_level[freq])

    return Curve(frequencies, boost, interpolation_alg=interpolation_alg)


def flat() -> Curve:
    """Return a flat 0 dB target."""
    return _create_target_curve({1: 0, 500: 0, 4000: 0, 25000: 0})


def linear() -> Curve:
    """Return the legacy flat target."""
    return flat()


def downwards_slope(factor: float = 1) -> Curve:
    return _create_target_curve({1: 0, 20000: -10 * factor})


def downwards_slope_linear_upper_mids(factor: float = 1) -> Curve:
    return _create_target_curve(
        {1: 0, 1000: -5 * factor, 6000: -5 * factor, 20000: -10 * factor, 25000: -10 * factor}
    )


def v_shape(factor: float = 1) -> Curve:
    return _create_target_curve(
        {1: -5, 20: 0, 100: 0, 300: -5 * factor, 3000: 0, 10000: -5 * factor, 20000: -10 * factor},
        "quadratic",
    )


def _finite_float(name: str, value: SupportsFloat) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(normalized):
        raise ValueError(f"{name} must be a finite number")
    return normalized


def _transition(
    frequency: float,
    from_frequency: float,
    to_frequency: float,
    from_level: float,
    to_level: float,
) -> float:
    if frequency <= from_frequency:
        return from_level
    if frequency >= to_frequency:
        return to_level
    position = math.log2(frequency / from_frequency) / math.log2(to_frequency / from_frequency)
    smooth_position = position * position * (3 - 2 * position)
    return from_level + (to_level - from_level) * smooth_position


def house_curve(
    bass_gain_db: SupportsFloat = 6.0,
    bass_start_hz: SupportsFloat = 80.0,
    bass_end_hz: SupportsFloat = 200.0,
    treble_gain_db: SupportsFloat = -2.0,
    treble_start_hz: SupportsFloat = 2_000.0,
    treble_end_hz: SupportsFloat = 20_000.0,
) -> Curve:
    """Return a smooth, configurable loudspeaker house curve.

    The bass gain remains constant below ``bass_start_hz`` and transitions
    smoothly to 0 dB at ``bass_end_hz``. The treble transition starts at
    ``treble_start_hz`` and reaches ``treble_gain_db`` at ``treble_end_hz``.
    Transitions use smoothstep interpolation on a logarithmic frequency axis.
    """
    bass_gain = _finite_float("bass_gain_db", bass_gain_db)
    bass_start = _finite_float("bass_start_hz", bass_start_hz)
    bass_end = _finite_float("bass_end_hz", bass_end_hz)
    treble_gain = _finite_float("treble_gain_db", treble_gain_db)
    treble_start = _finite_float("treble_start_hz", treble_start_hz)
    treble_end = _finite_float("treble_end_hz", treble_end_hz)

    if bass_start <= 0 or bass_start >= bass_end:
        raise ValueError("Bass transition frequencies must be positive and increasing")
    if treble_start <= 0 or treble_start >= treble_end:
        raise ValueError("Treble transition frequencies must be positive and increasing")

    frequencies = sorted(
        set(log_spaced(_TARGET_FROM_HZ, _TARGET_TO_HZ, _TARGET_RESOLUTION))
        | {bass_start, bass_end, treble_start, treble_end}
    )

    def evaluate(log_frequency: float) -> float:
        frequency = Curve.log**log_frequency
        return _transition(frequency, bass_start, bass_end, bass_gain, 0.0) + _transition(
            frequency,
            treble_start,
            treble_end,
            0.0,
            treble_gain,
        )

    levels = [evaluate(math.log(frequency, Curve.log)) for frequency in frequencies]
    return Curve(frequencies, levels, fun=evaluate)


def harman_room_2013() -> Curve:
    """Return a smooth approximation of the 2013 Harman in-room preference.

    AES Convention Paper 8994 reports a mean preferred loudspeaker response
    with about 6.6 dB of bass boost below 105 Hz and a -2.4 dB treble shelf
    above 2.5 kHz. This preset uses two-octave smooth transitions centered on
    those frequencies; it is not a digitization of a published graph.
    """
    return house_curve(
        bass_gain_db=6.6,
        bass_start_hz=52.5,
        bass_end_hz=210.0,
        treble_gain_db=-2.4,
        treble_start_hz=1_250.0,
        treble_end_hz=5_000.0,
    )


def from_rew_house_curve(file_path: str | PathLike[str]) -> Curve:
    """Load frequency/dB pairs from a REW-compatible house-curve file."""
    path = Path(file_path)
    if not path.is_file():
        raise ValueError(f"House-curve file does not exist: {file_path}")

    try:
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        content = path.read_text(encoding="cp1252")

    frequencies: list[float] = []
    levels: list[float] = []
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or (not line[0].isdigit() and line[0] not in "+-."):
            continue
        parts = re.split(r"[\s,]+", line)
        if len(parts) < 2:
            raise ValueError(f"Invalid house-curve row at line {line_number}: {raw_line!r}")
        try:
            frequency = float(parts[0])
            level = float(parts[1])
        except ValueError as exc:
            raise ValueError(
                f"Invalid house-curve row at line {line_number}: {raw_line!r}"
            ) from exc
        frequencies.append(frequency)
        levels.append(level)

    if len(frequencies) < 2:
        raise ValueError("House-curve file must contain at least two frequency/dB rows")
    return Curve(frequencies, levels)


def adjust_bass_target(
    target: Curve,
    measurements: Sequence[Measurement],
    max_boost: float = 5,
    upper_bound: float = 100,
) -> Curve:
    curves = [m.curve.smooth(Smoothing.SmoothingFactor.LIGHT_SMOOTHING) for m in measurements]
    avg = Curve.build_average_curve(curves)
    frequencies = avg.domain_frequencies

    y = []
    for x in frequencies:
        if x <= upper_bound:
            if target(x) > (avg(x) + max_boost):
                y.append(avg(x) + max_boost)
                continue
        y.append(target(x))
    tc = Curve(frequencies, y)

    return tc
