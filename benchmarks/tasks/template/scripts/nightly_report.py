"""Nightly cron entry point: emit a one-line summary of yesterday's log.

Runs outside the CLI; scheduled from crontab on the log host.
"""

import sys

from logsift.conf import MAX_LINES, COLOR  # noqa: F401  (COLOR reserved for the HTML variant)
from logsift import filters


def main(path):
    total = 0
    errors = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            entry = filters.parse_entry(line)
            if entry is None:
                continue
            total += 1
            if str(entry.get("level", "")).lower() == "error":
                errors += 1
            if total >= MAX_LINES:
                break
    print("nightly: {} entries, {} errors".format(total, errors))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
