"""
A weighting function takes two parameters.
iteration
pos: [0-1] determines the position of the frequency
"""
import math


def no_smoothing(iteration, pos):
    return 1


def exp_e_decrease(iteration, pos):
    return 1 / math.exp((1 + pos) * iteration)


def exp_2_decrease(iteration, pos):
    return 1 / 2 ** ((1 + pos) * iteration)


def exp_2_decrease_2(iteration, pos):
    return 1 / 2 ** ((1.1 + pos) ** iteration)

