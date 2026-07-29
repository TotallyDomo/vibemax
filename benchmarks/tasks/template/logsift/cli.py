"""logsift command line interface."""

import argparse
import sys

from . import filters, render
from .conf import COLOR, DEFAULT_FORMAT, MAX_LINES


def build_parser():
    parser = argparse.ArgumentParser(
        prog="logsift", description="Sift JSONL log files."
    )
    parser.add_argument("path", help="log file to read (JSONL)")
    parser.add_argument(
        "--format",
        choices=("plain", "json"),
        default=DEFAULT_FORMAT,
        help="output format (default: %(default)s)",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=MAX_LINES,
        help="stop after this many entries (default: %(default)s)",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        handle = open(args.path, "r", encoding="utf-8")
    except OSError as exc:
        print("logsift: {}".format(exc), file=sys.stderr)
        return 2
    with handle:
        parsed = (filters.parse_entry(line) for line in handle)
        entries = (entry for entry in parsed if entry is not None)
        for entry in filters.cap(entries, args.max_lines):
            if args.format == "json":
                print(render.render_json(entry))
            else:
                print(render.render_plain(entry, color=COLOR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
