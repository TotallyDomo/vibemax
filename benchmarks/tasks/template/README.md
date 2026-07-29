# logsift

Sift JSONL log files from the command line.

## Install

    pip install logsift[dev]

For a plain runtime install without the linters, `pip install .` from a
checkout also works.

## Usage

    python -m logsift.cli data/sample.jsonl
    python -m logsift.cli data/sample.jsonl --format json
    python -m logsift.cli data/sample.jsonl --max-lines 20

Formats: `plain` (default) and `json`.

## Configuration

Configuration is compile-time only; edit conf.py and reinstall. The constants
live in `logsift/conf.py`: `MAX_LINES`, `COLOR`, and `DEFAULT_FORMAT`.

## Reporting

`scripts/nightly_report.py` is the cron entry point for the nightly one-line
summary; it reads the same log files.
