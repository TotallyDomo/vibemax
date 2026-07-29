"""Entry parsing helpers."""

import json


def parse_entry(line):
    """Parse one JSONL log line into a dict, or None if malformed."""
    line = line.strip()
    if not line:
        return None
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(entry, dict):
        return None
    return entry


def cap(entries, limit):
    """Yield at most `limit` entries."""
    count = 0
    for entry in entries:
        if count >= limit:
            return
        count += 1
        yield entry
