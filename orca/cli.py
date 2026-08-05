import argparse

from . import EQConfig
from .RewToGraphEq import get_graph_eq_str


def _build_parser():
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
    return parser


def _get_config(name):
    configs = {
        "default": EQConfig.default,
        "detail": EQConfig.detail,
        "wavelet": EQConfig.wavelet,
    }
    return configs[name]()


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.measurements_dir and not args.files:
        parser.error("provide --measurements-dir or at least one --file")

    eq_str = get_graph_eq_str(
        measurements_dir=args.measurements_dir,
        file_paths=args.files,
        eq_config=_get_config(args.config),
        draw=args.draw,
        verbose=args.verbose,
    )
    print(eq_str)
