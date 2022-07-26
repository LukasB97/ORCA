import enum

from scipy.ndimage import gaussian_filter

class SMOOTHING_FACTOR(enum.Enum):
    NO_SMOOTHING = 0
    MIN_SMOOTHING = 2
    LIGHT_SMOOTHING = 4
    DEFAULT_SMOOTHING = 8
    STRONG_SMOOTHING = 16
    MAX_SMOOTHING = 32


def smooth_curve(points, smoothing_factor: SMOOTHING_FACTOR):
    """
    :param points:
    :param smoothing_factor:
    :return:
    """
    if not isinstance(smoothing_factor, SMOOTHING_FACTOR):
        raise ValueError("smoothing_factor must be an instance of the enum SMOOTHING_FACTOR")
    return gaussian_filter(points, sigma=smoothing_factor.value)
