"""Aggregate benchmark results + grades into per-cell tables and deltas.

Primary metric: visible output tokens per request (chars/4 estimate of assistant
text blocks; API output_tokens, which include thinking and tool payloads, are
reported alongside). Attention metrics: hidden-ask catch rate and gotcha
surfacing rate per cell. Emits results/summary-<tag>.md and .json.
"""

import argparse
import json
import random
import statistics
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent


def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def per_request(row, field):
    return row[field] / row["n_requests"]


def fmt(value, digits=1):
    if value is None:
        return "-"
    return ("%%.%df" % digits) % value


def bootstrap_delta_ci(blind_vals, vibe_vals, iters=10000, alpha=0.10):
    if not blind_vals or not vibe_vals:
        return None, None
    rng = random.Random(20260728)
    deltas = []
    for _ in range(iters):
        b = statistics.fmean(rng.choices(blind_vals, k=len(blind_vals)))
        v = statistics.fmean(rng.choices(vibe_vals, k=len(vibe_vals)))
        deltas.append(v - b)
    deltas.sort()
    lo = deltas[int(len(deltas) * (alpha / 2))]
    hi = deltas[int(len(deltas) * (1 - alpha / 2)) - 1]
    return lo, hi


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    results = [r for r in load_jsonl(BENCH_DIR / "results" / (args.tag + ".jsonl")) if r.get("status") == "ok"]
    grades = {g["job_id"]: g for g in load_jsonl(BENCH_DIR / "grades" / (args.tag + ".jsonl"))}

    models = sorted({r["model"] for r in results})
    tasks = sorted({r["task"] for r in results})
    conds = ["blind", "vibemax"]

    def cell(model, task, cond):
        return [r for r in results if r["model"] == model and r["task"] == task and r["cond"] == cond]

    summary = {"tag": args.tag, "cells": [], "models": {}}
    lines = ["# Benchmark summary: %s" % args.tag, ""]

    lines += ["## Visible output tokens per request (chars/4 estimate)", ""]
    lines.append("| model | task | n blind/vibemax | blind | vibemax | delta |")
    lines.append("|---|---|---|---|---|---|")
    for model in models:
        for task in tasks:
            blind = [per_request(r, "visible_est_tokens_total") for r in cell(model, task, "blind")]
            vibe = [per_request(r, "visible_est_tokens_total") for r in cell(model, task, "vibemax")]
            if not blind and not vibe:
                continue
            mb = statistics.fmean(blind) if blind else None
            mv = statistics.fmean(vibe) if vibe else None
            delta = (mv - mb) if (mb is not None and mv is not None) else None
            lines.append("| %s | %s | %d/%d | %s | %s | %s |" % (
                model, task, len(blind), len(vibe), fmt(mb), fmt(mv), fmt(delta)
            ))
            summary["cells"].append({
                "model": model, "task": task,
                "n_blind": len(blind), "n_vibemax": len(vibe),
                "visible_tok_per_req_blind": mb,
                "visible_tok_per_req_vibemax": mv,
                "visible_tok_per_req_delta": delta,
            })
    lines.append("")

    lines += ["## Pooled per model (all tasks, per-request, session-weighted)", ""]
    lines.append("| model | blind | vibemax | delta | 90% CI (bootstrap) | api-out blind | api-out vibemax |")
    lines.append("|---|---|---|---|---|---|---|")
    for model in models:
        blind_rows = [r for r in results if r["model"] == model and r["cond"] == "blind"]
        vibe_rows = [r for r in results if r["model"] == model and r["cond"] == "vibemax"]
        blind = [per_request(r, "visible_est_tokens_total") for r in blind_rows]
        vibe = [per_request(r, "visible_est_tokens_total") for r in vibe_rows]
        if not blind or not vibe:
            continue
        mb, mv = statistics.fmean(blind), statistics.fmean(vibe)
        lo, hi = bootstrap_delta_ci(blind, vibe)
        ab = statistics.fmean([per_request(r, "api_output_tokens_total") for r in blind_rows])
        av = statistics.fmean([per_request(r, "api_output_tokens_total") for r in vibe_rows])
        lines.append("| %s | %s | %s | %s | [%s, %s] | %s | %s |" % (
            model, fmt(mb), fmt(mv), fmt(mv - mb), fmt(lo), fmt(hi), fmt(ab, 0), fmt(av, 0)
        ))
        summary["models"][model] = {
            "visible_tok_per_req_blind": mb,
            "visible_tok_per_req_vibemax": mv,
            "delta": mv - mb,
            "delta_ci90": [lo, hi],
            "api_out_per_req_blind": ab,
            "api_out_per_req_vibemax": av,
            "n_sessions": [len(blind), len(vibe)],
        }
    lines.append("")

    def rate(rows, field):
        vals = [grades.get(r["job_id"], {}).get(field) for r in rows]
        vals = [v for v in vals if v is not None]
        if not vals:
            return None, 0
        return sum(1 for v in vals if v) / len(vals), len(vals)

    for metric, field, applicable in (
        ("Hidden-ask catch rate", "hidden_ask_final", ("t3", "t5")),
        ("Gotcha surfacing rate", "gotcha_final", ("t3", "t5")),
    ):
        lines += ["## %s" % metric, ""]
        lines.append("| model | task | blind | vibemax |")
        lines.append("|---|---|---|---|")
        for model in models:
            for task in tasks:
                if task not in applicable:
                    continue
                rb, nb = rate(cell(model, task, "blind"), field)
                rv, nv = rate(cell(model, task, "vibemax"), field)
                if nb == 0 and nv == 0:
                    continue
                lines.append("| %s | %s | %s (n=%d) | %s (n=%d) |" % (
                    model, task,
                    fmt(rb, 2) if rb is not None else "-", nb,
                    fmt(rv, 2) if rv is not None else "-", nv,
                ))
                summary["cells"].append({
                    "model": model, "task": task, "metric": field,
                    "blind": rb, "vibemax": rv, "n_blind": nb, "n_vibemax": nv,
                })
        lines.append("")

    lines += ["## Quality guardrails (grader, approximate)", ""]
    lines.append("| model | cond | task_completed mean (0-2) | report_quality mean (1-5) | graded n |")
    lines.append("|---|---|---|---|---|")
    for model in models:
        for cond in conds:
            rows = [r for r in results if r["model"] == model and r["cond"] == cond]
            tc = [grades.get(r["job_id"], {}).get("task_completed") for r in rows]
            rq = [grades.get(r["job_id"], {}).get("report_quality") for r in rows]
            tc = [v for v in tc if isinstance(v, (int, float))]
            rq = [v for v in rq if isinstance(v, (int, float))]
            if not tc and not rq:
                continue
            lines.append("| %s | %s | %s | %s | %d |" % (
                model, cond,
                fmt(statistics.fmean(tc), 2) if tc else "-",
                fmt(statistics.fmean(rq), 2) if rq else "-",
                max(len(tc), len(rq)),
            ))
    lines.append("")

    total_cost = sum(r.get("cost_usd_total") or 0 for r in results)
    grader_cost = sum(g.get("grader_cost_usd") or 0 for g in grades.values())
    failed = load_jsonl(BENCH_DIR / "results" / (args.tag + ".jsonl"))
    n_failed = sum(1 for r in failed if r.get("status") != "ok")
    lines += [
        "## Run accounting", "",
        "- ok sessions: %d; failed rows: %d" % (len(results), n_failed),
        "- session cost (list-equivalent): $%.2f; grader cost: $%.2f" % (total_cost, grader_cost),
        "",
    ]
    summary["accounting"] = {
        "ok_sessions": len(results), "failed_rows": n_failed,
        "session_cost_usd": total_cost, "grader_cost_usd": grader_cost,
    }

    out_md = BENCH_DIR / "results" / ("summary-%s.md" % args.tag)
    out_json = BENCH_DIR / "results" / ("summary-%s.json" % args.tag)
    out_md.write_text("\n".join(lines), encoding="utf-8")
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
