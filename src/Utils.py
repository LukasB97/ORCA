import math


def log_to_hz(value, base, start_value=1):
    return start_value * base ** value

def hz_to_log(value, base, starting_value=1):
    return math.log(value / starting_value, base)

def get_log_base(freqs):
    return freqs[-1] / freqs[-2]

def convert_hz_to_log_scale(freqs):
    base = get_log_base(freqs)
    log_x = []
    for i in range(len(freqs)):
        log_x.append(i)
    return log_x, base

