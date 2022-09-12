import glob
import os
from typing import List

from src.Curve import Curve


def read_hz_and_spl(rew_str):
    """
    Reads the (Hz, Spl) pairs from the text in the exported rew file
    :param rew_str:
    :return:
    """
    start = False
    freqs = []
    spls = []
    for line in rew_str.split("\n"):
        if line and start:
            [freq, spl, _] = line.split(" ")
            freq = float(freq)
            spl = round(float(spl), 1)
            if freq >= 20:
                freqs.append(freq)
                spls.append(spl)
        elif "Freq(Hz) SPL(dB)" in line:
            start = True
    return freqs, spls


def get_all_txt_files(dir_path):
    files = []
    os.chdir(dir_path)
    for file in glob.glob("*.txt"):
        files.append(file)
    return files


def curve_from_rew_file(rew_file_path):
    content = open(rew_file_path, "r").read()
    freqs, spls = read_hz_and_spl(content)
    return Curve(freqs, spls)


def get_files(dir_path=None, file_paths: List[str] = None):
    if not file_paths and not dir_path:
        raise ValueError("dir_path and file_paths cannot both be None")
    if not file_paths:
        file_paths = []
    elif isinstance(file_paths, str):
        file_paths = [file_paths]
    if dir_path:
        file_paths.extend(get_all_txt_files(dir_path))
    return file_paths
