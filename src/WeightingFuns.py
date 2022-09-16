"""
A weighting function takes two parameters.
iteration
pos: [0-1] determines the position of the frequency
"""
import math


def no_smoothing(iteration, pos):
    return 1


def exp_decrease(iteration, pos):
    return 1 / math.exp(pos * iteration * 1.5)
