from src.Curve import Curve


def linear():
    return Curve.create_target_curve({
        1: 0,
        500: 0,
        4000: 0,
        25000: 0
    })

def downwards_slope(drop_off_freq=100, drop=-7.5):
    return Curve.create_target_curve({
        1: 0,
        drop_off_freq: 0,
        20000: drop,
        25000: drop
    })

def downwards_slope_linear_upper_mids(drop_off_freq=100, drop=-7.5):
    return Curve.create_target_curve({
        1: 0,
        drop_off_freq: 0,
        20000: drop,
        25000: drop
    })

def v_shape(boost=5):
    return Curve.create_target_curve({
        1: 0,
        100: boost,
        300: (-1) * boost,
        800: 0,
        3000: boost,
        10000: 0,
        20000: -5
    })