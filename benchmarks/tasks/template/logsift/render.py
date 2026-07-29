"""Renderers for parsed log entries."""

import datetime
import json

# The bundled sample data mixes two timestamp shapes: epoch seconds as a
# float and ISO-8601 strings. JSON output normalizes every ts to ISO-8601
# via normalize_ts; plain output prints ts exactly as it appears in the file.


def normalize_ts(ts):
    """Return ts as an ISO-8601 string, accepting epoch floats or ISO strings."""
    if isinstance(ts, (int, float)):
        return datetime.datetime.fromtimestamp(
            ts, tz=datetime.timezone.utc
        ).isoformat()
    return str(ts)


def render_plain(entry, color=False):
    level = str(entry.get("level", "info")).upper()
    line = "{} [{}] {}".format(entry.get("ts", "-"), level, entry.get("msg", ""))
    if color and level in ("WARN", "ERROR"):
        line = "\x1b[31m" + line + "\x1b[0m"
    return line


def render_json(entry):
    out = dict(entry)
    if "ts" in out:
        out["ts"] = normalize_ts(out["ts"])
    return json.dumps(out, sort_keys=True)
