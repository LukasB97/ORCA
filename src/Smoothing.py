import enum

from scipy.ndimage import gaussian_filter


class SmoothingFactor(enum.Enum):
    MAX_SMOOTHING = 32
    STRONG_SMOOTHING = 16
    DEFAULT_SMOOTHING = 8
    LIGHT_SMOOTHING = 4
    MIN_SMOOTHING = 2
    NO_SMOOTHING = 0


def smooth_curve(points, smoothing_factor: SmoothingFactor):
    """
    :param points: array of values to smooth
    :param smoothing_factor: Determines the strength of the smoothing process
    :return:
    """
    if not isinstance(smoothing_factor, SmoothingFactor):
        raise ValueError("smoothing_factor must be an instance of the enum SMOOTHING_FACTOR")
    return gaussian_filter(points, sigma=smoothing_factor.value)
