from pathlib import Path

from orca import TargetCurves, create_eq, format_eq_str, get_graph_eq_str
from orca.EQConfig import EQConfig

EXAMPLE_MEASUREMENTS = Path(__file__).parent / "example measurements"


def basic_directory_example() -> str:
    return get_graph_eq_str(measurements_dir=str(EXAMPLE_MEASUREMENTS))


def custom_target_curve_example() -> str:
    target_curve = TargetCurves.house_curve(
        bass_gain_db=4.0,
        treble_gain_db=-1.5,
    )
    return get_graph_eq_str(
        measurements_dir=str(EXAMPLE_MEASUREMENTS),
        target_curve=target_curve,
    )


def custom_eq_config_example() -> str:
    eq_config = EQConfig.from_range(eq_res=256, eq_from=30, eq_to=18000)
    return get_graph_eq_str(
        measurements_dir=str(EXAMPLE_MEASUREMENTS),
        eq_config=eq_config,
    )


def custom_weighting_example() -> str:
    def weighting(iteration: int, pos: float) -> float:
        return 1 / (1 + pos) ** iteration

    eq_config = EQConfig(weighting_fun=weighting)
    return get_graph_eq_str(
        measurements_dir=str(EXAMPLE_MEASUREMENTS),
        eq_config=eq_config,
    )


def curve_access_example() -> str:
    eq = create_eq(measurements_dir=str(EXAMPLE_MEASUREMENTS))
    eq.draw("Equalizer")
    eq(1000)
    return format_eq_str(eq)


if __name__ == "__main__":
    print(basic_directory_example())
