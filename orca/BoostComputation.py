import math

from scipy.optimize import minimize_scalar


def _err(target, current, boost):
    return 2 ** (abs(target - current - boost) / 10)


def _create_fun_to_minimize(target, spl):
    def fun(boost):
        try:
            boost = float(boost[0])
        except (TypeError, IndexError):
            boost = float(boost)

        errs = 0
        for level in spl:
            errs += _err(target, level, boost)
        return (1 / len(spl)) * errs
    return fun


def minimize(target, spl):
    if not spl:
        raise ValueError("At least one SPL value is required")

    fun_to_minimize = _create_fun_to_minimize(target, spl)
    lower = target - max(spl)
    upper = target - min(spl)
    if math.isclose(lower, upper):
        return lower

    result = minimize_scalar(
        fun_to_minimize,
        bounds=(lower, upper),
        method="bounded",
    )
    if not result.success:
        raise RuntimeError(f"Boost optimization failed: {result.message}")
    return result.x

