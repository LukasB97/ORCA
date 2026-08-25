import os
import math
from pathlib import Path
from typing import List

from .Curve import Curve


def _parse_rew_float(value, raw_line):
    try:
        return float(value)
    except ValueError:
        if "," in value and "." not in value:
            try:
                return float(value.replace(",", "."))
            except ValueError:
                pass
        raise ValueError(f"Invalid REW data row: {raw_line!r}")


def read_hz_and_spl(rew_str):
    """
    Reads the (Hz, dB) pairs from the text in the exported rew file
    :param rew_str:
    :return:
    """
    start = False
    saw_header = False
    frequencies = []
    sp_levels = []
    for raw_line in rew_str.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if start:
            if line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) < 2:
                raise ValueError(f"Invalid REW data row: {raw_line!r}")
            freq = _parse_rew_float(parts[0], raw_line)
            spl = round(_parse_rew_float(parts[1], raw_line), 1)
            if not math.isfinite(freq) or not math.isfinite(spl):
                raise ValueError(f"Invalid REW data row: {raw_line!r}")
            if freq >= 20:
                frequencies.append(freq)
                sp_levels.append(spl)
        elif "Freq(Hz)" in line and "SPL" in line:
            start = True
            saw_header = True

    if not saw_header:
        raise ValueError("No REW frequency/SPL header found")
    if not frequencies:
        raise ValueError("No REW frequency/SPL data found at or above 20 Hz")

    return frequencies, sp_levels


def get_all_txt_files(dir_path):
    path = Path(dir_path)
    if not path.is_dir():
        raise ValueError(f"Measurement directory does not exist: {dir_path}")
    return [str(file_path) for file_path in sorted(path.glob("*.txt"))]


def curve_from_rew_file(rew_file_path):
    path = Path(rew_file_path)
    if not path.is_file():
        raise ValueError(f"Measurement file does not exist: {rew_file_path}")

    try:
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        content = path.read_text(encoding="cp1252")
    frequencies, sp_levels = read_hz_and_spl(content)
    return Curve(frequencies, sp_levels)


def get_files(dir_path=None, file_paths: List[str] = None):
    if not file_paths and not dir_path:
        raise ValueError("dir_path and file_paths cannot both be None")
    if not file_paths:
        file_paths = []
    elif isinstance(file_paths, (str, os.PathLike)):
        file_paths = [str(file_paths)]
    else:
        file_paths = list(file_paths)
    if dir_path:
        file_paths.extend(get_all_txt_files(dir_path))
    if not file_paths:
        raise ValueError("No measurement files found")
    return file_paths
