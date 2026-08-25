from pathlib import Path

from orca import TargetCurves
from orca.EQConfig import EQConfig
from orca.RewToGraphEq import create_eq, format_eq_str, get_graph_eq_str


EXAMPLE_MEASUREMENTS = Path(__file__).parent / "example measurements"


def basic_directory_example():
    return get_graph_eq_str(measurements_dir=str(EXAMPLE_MEASUREMENTS))


def custom_target_curve_example():
    target_curve = TargetCurves.downwards_slope(factor=0.5)
    return get_graph_eq_str(
        measurements_dir=str(EXAMPLE_MEASUREMENTS),
        target_curve=target_curve,
    )


def custom_eq_config_example(calculation_res=512):
    eq_config = EQConfig(eq_res=256, eq_from=30, eq_to=18000)
    return get_graph_eq_str(
        measurements_dir=str(EXAMPLE_MEASUREMENTS),
        eq_config=eq_config,
        calculation_res=calculation_res,
    )


def custom_weighting_example():
    def weighting(iteration, pos):
        return 1 / (1 + pos) ** iteration

    eq_config = EQConfig(weighting_fun=weighting)
    return get_graph_eq_str(
        measurements_dir=str(EXAMPLE_MEASUREMENTS),
        eq_config=eq_config,
    )


def curve_access_example():
    eq = create_eq(measurements_dir=str(EXAMPLE_MEASUREMENTS))
    eq.draw("Equalizer")
    eq(1000)
    return format_eq_str(eq)


if __name__ == "__main__":
    print(basic_directory_example())
