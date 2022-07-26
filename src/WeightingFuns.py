"""
A weighting function takes two parameters.
iteration
pos: [0-1] determines the position of the frequency

Linear/exponential... describes the type of function in the denominator
"""
import math




def no_smoothing():
    def f(iteration, pos):
        return 1
    return f


def linear(iteration_influence=1.5):
    def f(iteration, pos):
        return 1 / ((1.1 + pos) ** (1 + iteration * iteration_influence))
    return f


def exp_e_decrease(iteration_influence=1):
    def f(iteration, pos):
        return 1 / math.exp((1 + pos) * iteration * iteration_influence)
    return f



def exp_2_decrease(iteration_influence=1):
    def f(iteration, pos):
        return 1 / 2 ** ((1 + pos) * iteration * iteration_influence)
    return f


def exp_2_decrease_2(iteration_influence=1):
    def f(iteration, pos):
        return 1 / 2 ** ((1 + pos) ** (iteration * iteration_influence))
    return f


# def build_linear(start_impact, end_impact):
#     s = [start_impact, end_impact]
#     s = [ss / float(len(Smoothing.SmoothingFactor)) for ss in s]
#     f = interp1d([0, 1], s)
#     def fun(iteration, pos):
#         return 1 / f(pos) * (1 + iteration)
#
#         print(len(Smoothing.SmoothingFactor))
