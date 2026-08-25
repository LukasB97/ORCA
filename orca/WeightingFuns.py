"""Weighting functions receive an iteration index and a normalized frequency."""


def no_smoothing():
    def f(iteration, pos):
        return 1
    return f


def linear(iteration_influence=1.5):
    def f(iteration, pos):
        return 1 / ((1.1 + pos) ** (1 + iteration * iteration_influence))
    return f
