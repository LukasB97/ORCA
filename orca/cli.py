from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence

from . import TargetCurves, Wavelet
from .Curve import Curve, PlottingDependencyError
from .EQConfig import EQConfig
from .RewToGraphEq import DEFAULT_REFERENCE_RANGE, get_graph_eq_str


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a GraphicEQ string from REW measurement exports."
    )
    parser.add_argument(
        "--measurements-dir",
        help="Directory containing REW .txt measurement exports.",
    )
    parser.add_argument(
        "--file",
        dest="files",
        action="append",
        help="REW .txt measurement export. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--config",
        choices=("default", "detail", "wavelet"),
        default="default",
        help="EQ point layout to use.",
    )
    parser.add_argument(
        "--target",
        choices=("flat", "house", "harman-room-2013"),
        default="flat",
        help="Target-curve preset to use (default: flat).",
    )
    parser.add_argument(
        "--target-file",
        help="REW-compatible house-curve file to use instead of a preset.",
    )
    parser.add_argument(
        "--eq-from",
        type=float,
        help="Lower frequency bound for a custom EQ point grid.",
    )
    parser.add_argument(
        "--eq-to",
        type=float,
        help="Upper frequency bound for a custom EQ point grid.",
    )
    parser.add_argument(
        "--eq-res",
        type=int,
        help="Number of points in a custom EQ grid (default: 128).",
    )
    parser.add_argument(
        "--draw",
        action="store_true",
        help="Show diagnostic plots while creating the equalizer.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print diagnostic error estimates.",
    )
    parser.add_argument(
        "--reference-from",
        type=float,
        help=f"Lower frequency bound used for SPL normalization (default: {DEFAULT_REFERENCE_RANGE[0]:g} Hz).",
    )
    parser.add_argument(
        "--reference-to",
        type=float,
        help=f"Upper frequency bound used for SPL normalization (default: {DEFAULT_REFERENCE_RANGE[1]:g} Hz).",
    )
    return parser


def _get_config(
    name: str,
    eq_from: float | None = None,
    eq_to: float | None = None,
    eq_res: int | None = None,
) -> EQConfig:
    if eq_from is not None and eq_to is not None:
        return EQConfig.from_range(
            eq_from=eq_from,
            eq_to=eq_to,
            eq_res=128 if eq_res is None else eq_res,
        )

    configs: dict[str, Callable[[], EQConfig]] = {
        "default": EQConfig,
        "detail": lambda: EQConfig.from_range(eq_res=256),
        "wavelet": Wavelet.config,
    }
    return configs[name]()


def _get_target_curve(name: str, target_file: str | None = None) -> Curve:
    if target_file is not None:
        return TargetCurves.from_rew_house_curve(target_file)
    targets: dict[str, Callable[[], Curve]] = {
        "flat": TargetCurves.flat,
        "house": TargetCurves.house_curve,
        "harman-room-2013": TargetCurves.harman_room_2013,
    }
    return targets[name]()


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.measurements_dir and not args.files:
        parser.error("provide --measurements-dir or at least one --file")
    if (args.reference_from is None) != (args.reference_to is None):
        parser.error("provide --reference-from and --reference-to together")
    custom_eq_requested = any(
        value is not None for value in (args.eq_from, args.eq_to, args.eq_res)
    )
    if custom_eq_requested and (args.eq_from is None or args.eq_to is None):
        parser.error("provide --eq-from and --eq-to together; --eq-res is optional")
    if custom_eq_requested and args.config != "default":
        parser.error("custom EQ bounds cannot be combined with --config detail or wavelet")
    if args.target_file is not None and args.target != "flat":
        parser.error("--target-file cannot be combined with a non-flat --target preset")

    reference_range = DEFAULT_REFERENCE_RANGE
    if args.reference_from is not None and args.reference_to is not None:
        reference_range = (args.reference_from, args.reference_to)

    try:
        eq_str = get_graph_eq_str(
            measurements_dir=args.measurements_dir,
            file_paths=args.files,
            eq_config=_get_config(
                args.config,
                eq_from=args.eq_from,
                eq_to=args.eq_to,
                eq_res=args.eq_res,
            ),
            target_curve=_get_target_curve(args.target, args.target_file),
            draw=args.draw,
            verbose=args.verbose,
            reference_range=reference_range,
        )
    except (OSError, PlottingDependencyError, ValueError) as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")
    print(eq_str)


if __name__ == "__main__":
    main()
