import math


def log_to_hz(base, multiplier, value):
    return base * multiplier ** value

def hz_to_log(base, multiplier, value):
    return math.log(value / base, multiplier)

def get_log_base_multiplier(freqs):
    return freqs[0], freqs[-1] / freqs[-2]

def convert_hz_to_log_scale(freqs):
    base, multiplier = get_log_base_multiplier(freqs)
    log_x = []
    for i in range(len(freqs)):
        log_x.append(i)
    return log_x, base, multiplier

