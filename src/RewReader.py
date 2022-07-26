import re


def read_hz_and_spl(rew_str):
    start = re.search(r'Start Frequency: ([0-9.]+) Hz', rew_str).group(1)
    start = False
    steps = []
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
        elif "Freq(Hz) SPL(dB) Phase(degrees)" in line:
            start = True
    return freqs, spls