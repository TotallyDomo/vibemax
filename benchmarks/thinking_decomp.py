"""Post-hoc thinking-vs-visible token decomposition over raw stream-json transcripts.

Reads results/<tag>.jsonl for job metadata and the raw <raw-root>/<tag>/<job>/turn*.jsonl
streams, estimates tokens as chars/4 over assistant thinking/text/tool_use blocks, and reports
per-cell (model x task x cond) per-request means plus vibemax-blind deltas with SE.

Only haiku streams carry thinking text; sonnet/opus/fable emit signature-only thinking
blocks, so their thinking is estimated as the residual
    api_output_tokens - text_est - tool_use_est
which also absorbs structural overhead (scales with api turns). Haiku has both the
direct and residual figures, validating the residual method.

Post-hoc only: reads frozen-run artifacts, never part of the harness. Re-runnable:
    python thinking_decomp.py --tag grid [--model sonnet]
"""

import argparse
import glob
import json
import math
import os
import tempfile
from collections import defaultdict

# Must match harness.py's DEFAULT_RAW_ROOT: $VIBEMAX_BENCH_RAW, else <tempdir>/vibemax-bench.
DEF_RAW_ROOT = os.environ.get("VIBEMAX_BENCH_RAW") or os.path.join(
    tempfile.gettempdir(), "vibemax-bench"
)


def job_stream_totals(raw_dir):
    """Sum chars of thinking and text blocks across all turn*.jsonl in one job dir."""
    think_chars = 0
    text_chars = 0
    tool_chars = 0
    files = sorted(glob.glob(os.path.join(raw_dir, "turn*.jsonl")))
    if not files:
        return None
    for path in files:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") != "assistant":
                    continue
                for blk in ev.get("message", {}).get("content", []):
                    if blk.get("type") == "thinking":
                        think_chars += len(blk.get("thinking", ""))
                    elif blk.get("type") == "text":
                        text_chars += len(blk.get("text", ""))
                    elif blk.get("type") == "tool_use":
                        tool_chars += len(json.dumps(blk.get("input", {})))
    return think_chars, text_chars, tool_chars


def mean_se(values):
    n = len(values)
    if n == 0:
        return float("nan"), float("nan")
    m = sum(values) / n
    if n == 1:
        return m, float("nan")
    var = sum((v - m) ** 2 for v in values) / (n - 1)
    return m, math.sqrt(var / n)


def delta_se(a, b):
    """SE of mean(a) - mean(b) for independent samples."""
    ma, sa = mean_se(a)
    mb, sb = mean_se(b)
    if math.isnan(sa) or math.isnan(sb):
        return ma - mb, float("nan")
    return ma - mb, math.sqrt(sa ** 2 + sb ** 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="grid")
    ap.add_argument("--raw-root", default=DEF_RAW_ROOT)
    ap.add_argument("--results", default=None, help="results jsonl (default results/<tag>.jsonl)")
    ap.add_argument("--model", default=None, help="restrict to one model key, e.g. sonnet")
    args = ap.parse_args()

    results_path = args.results or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "results", args.tag + ".jsonl"
    )
    raw_root = os.path.join(args.raw_root, args.tag)

    # cells[(model, task, cond)] = list of per-request metric dicts, one entry per ok job
    cells = defaultdict(list)
    missing_raw = []
    with open(results_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("status") != "ok":
                continue
            if args.model and row["model"] != args.model:
                continue
            totals = job_stream_totals(os.path.join(raw_root, row["job_id"]))
            if totals is None:
                missing_raw.append(row["job_id"])
                continue
            think_chars, text_chars, tool_chars = totals
            n_req = row.get("n_requests") or 1
            api_turns = sum(t.get("num_api_turns", 0) for t in row.get("turns", []))
            api_out = row.get("api_output_tokens_total", 0)
            cells[(row["model"], row["task"], row["cond"])].append({
                "think_tok": think_chars / 4.0 / n_req,
                "text_tok": text_chars / 4.0 / n_req,
                "tool_tok": tool_chars / 4.0 / n_req,
                "resid_tok": (api_out - text_chars / 4.0 - tool_chars / 4.0) / n_req,
                "api_out": api_out / n_req,
                "api_turns": api_turns / n_req,
            })

    if missing_raw:
        print("WARN missing raw dirs for %d ok rows: %s" % (
            len(missing_raw), ", ".join(missing_raw[:5]) + ("..." if len(missing_raw) > 5 else "")))

    models = sorted({k[0] for k in cells})
    tasks = sorted({k[1] for k in cells})
    metrics = [("think_tok", "thinking tok/req"), ("text_tok", "text tok/req"),
               ("tool_tok", "tool_use tok/req"), ("resid_tok", "residual tok/req"),
               ("api_out", "api output tok/req"), ("api_turns", "api turns/req")]

    for model in models:
        print("\n=== %s ===" % model)
        header = "%-20s %-6s %10s %10s %18s" % ("metric", "task", "blind", "vibemax", "delta (SE)")
        print(header)
        print("-" * len(header))
        for mkey, mlabel in metrics:
            for task in tasks:
                blind = [j[mkey] for j in cells.get((model, task, "blind"), [])]
                vmax = [j[mkey] for j in cells.get((model, task, "vibemax"), [])]
                if not blind or not vmax:
                    continue
                mb, _ = mean_se(blind)
                mv, _ = mean_se(vmax)
                d, se = delta_se(vmax, blind)
                se_s = "nan" if math.isnan(se) else "%.0f" % se if abs(se) >= 10 else "%.1f" % se
                print("%-20s %-6s %10.1f %10.1f %+12.1f (%s)  n=%d/%d" % (
                    mlabel, task, mb, mv, d, se_s, len(blind), len(vmax)))
        print()


if __name__ == "__main__":
    main()
