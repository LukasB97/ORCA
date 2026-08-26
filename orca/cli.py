from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence

from . import Wavelet
from .Curve import PlottingDependencyError
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


def _get_config(name: str) -> EQConfig:
    configs: dict[str, Callable[[], EQConfig]] = {
        "default": EQConfig,
        "detail": lambda: EQConfig.from_range(eq_res=256),
        "wavelet": Wavelet.config,
    }
    return configs[name]()


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.measurements_dir and not args.files:
        parser.error("provide --measurements-dir or at least one --file")
    if (args.reference_from is None) != (args.reference_to is None):
        parser.error("provide --reference-from and --reference-to together")

    reference_range = DEFAULT_REFERENCE_RANGE
    if args.reference_from is not None and args.reference_to is not None:
        reference_range = (args.reference_from, args.reference_to)

    try:
        eq_str = get_graph_eq_str(
            measurements_dir=args.measurements_dir,
            file_paths=args.files,
            eq_config=_get_config(args.config),
            draw=args.draw,
            verbose=args.verbose,
            reference_range=reference_range,
        )
    except (OSError, PlottingDependencyError, ValueError) as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")
    print(eq_str)


if __name__ == "__main__":
    main()
