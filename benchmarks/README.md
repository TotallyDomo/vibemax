# benchmarks

The A/B harness for the controlled blind-vs-vibemax comparison; measured
results live in `RESULTS.md`. (The per-request narration figure in the
top-level README is production telemetry - a separate, observational evidence
source, not produced by this harness.) Two conditions - `blind` (no style) and
`vibemax` (the contract injected the way the CLAUDE.md default-on install
does, via an appended system prompt) - across three scripted multi-turn tasks
and a model grid, run headless through `claude -p`.

## What it measures

- **Visible output tokens per request** - chars/4 estimate over the assistant's
  visible text blocks (API `output_tokens`, which also count thinking and tool
  payloads, are recorded alongside).
- **Hidden-ask catch rate** - the 3- and 5-turn tasks bury a secondary request
  mid-message; a deterministic file check plus a blinded grader decide whether
  it was caught.
- **Gotcha surfacing** - each of those tasks also plants a repo fact that
  contradicts a naive reading of the ask (mixed timestamp formats; an
  undocumented consumer of a module being migrated away). Scored by the grader,
  with a regex audit column.
- **Quality guardrails** - grader-scored task completion (0-2) and report
  quality (1-5), to catch a condition winning tokens by dropping work.

## Layout

- `tasks/template/` - the sandbox repo (a small JSONL log-sifting CLI) every
  session starts from; `tasks/tasks.json` - the scripted turns and scoring keys.
- `contract-vibemax.md` - the contract as injected in grid v1: SKILL.md's body,
  frontmatter stripped, kept exactly as run. The shipped SKILL.md has since renamed
  the "Gotchas" category to "Caveats" (label only, rules identical), so the two
  differ by that word. Regenerate only for a new run.
- `harness.py` - driver (sandboxing, retries, checkpointed results jsonl).
- `grade.py` - deterministic checks merged with a fixed Haiku rubric pass.
- `analyze.py` - per-cell tables, pooled deltas, bootstrap CI.
- `smoke_probe.py` - run first: checks the sandbox for an enclosing
  CLAUDE.md/AGENTS.md, hook and enclosing-agent-config leakage into children,
  auth path, model IDs, resume mechanics. The leakage check is limited to the
  `VIBEMAX_PROBE_MARKERS` strings you configure to match *your* enclosing
  setup - a CLEAN verdict is not proof of isolation beyond those markers. Both
  the probe and harness refuse a raw root beneath an agent-config file before
  starting any paid child session.
- `hooks-off.json` - settings overlay passed to every child session.
- `grid.json` / `pilot.json` - the full grid and the smoke-gate pilot.

## Running

From this directory:

    python smoke_probe.py
    python harness.py --config pilot.json     # smoke gate only, excluded from stats
    python harness.py --config grid.json
    python grade.py --tag grid
    python analyze.py --tag grid

Raw stream-json and sandboxes land under `<tempdir>/vibemax-bench/` by default -
set `VIBEMAX_BENCH_RAW` or pass `--raw-dir` to move them; summarized rows land in
`results/<tag>.jsonl`. A redirected tempdir can itself sit under CLAUDE.md or
AGENTS.md; if the preflight names one, choose a raw root outside that tree.

The published `results/*.jsonl` keep each job's absolute sandbox path with the
author's local root swapped for a neutral one. The substitutions are
equal-length, so every recorded character and token count in those rows is the
measured value, byte-for-byte unchanged.

## Run discipline

The pilot exists to catch hard errors only. After it, harness + tasks + configs
are frozen (`freeze.txt` records their hashes) and the full grid runs fresh,
pilot rows excluded, with no per-cell re-runs after seeing numbers. Retries
happen only for infrastructure failures (timeouts, rate limits), never because
of a result.

Rules added 2026-07-28 after the first grid ran on a harness defect
(children ran without Bash allowlisted, so every verification command was
permission-denied; models beg differently, which contaminated visible-output
numbers - and the haiku-only pilot's pass/fail checks never surfaced it,
though the denials sit plainly in its raw streams, which nobody read):

- **Full permissions in the sandbox.** Children run `bypassPermissions` inside
  their scrubbed, git-inited sandbox. Never ship an allowlist that silently
  denies a tool class the tasks assume; the sandbox is the safety boundary,
  not the permission gate.
- **Staged rollout, cheapest model first.** One model block at a time -
  haiku, then sonnet, then opus, then fable - with a gate between blocks:
  read a sample of raw transcripts (not just exit checks) and reconcile
  spend before the next block starts. Never launch every model in one shot.
- **Stop on anomaly.** Any systematic pattern in transcripts that the design
  did not intend - repeated permission denials, retry loops, a model coping
  with the environment instead of doing the task - halts the run before the
  next block. A running grid is never too frozen to stop; freezing protects
  results from cherry-picking, not defects from scrutiny.
- **Budget from measured numbers, dollars first.** Quote projected cost in
  list-USD from measured per-model actuals, name the denominator of any
  percentage, and reconcile spend after every block by pricing the raw
  transcripts (the harness records `cost_usd_total` per row). Budget the
  interactive sessions around a benchmark (review, analysis, debugging) too:
  on grid v1 they added roughly 0.4x the run cost (measured from the
  author's session telemetry, which lives outside this repo). Never quote a
  budget figure that lacks a measured source.

## Extending

Conditions are just system-prompt injections: to add an arm (a compression
style, a bare "be concise" one-liner), add a condition name and its injection
file to the config and harness condition map. The DESIGN.md comparison plan
names those arms as future work; they were not part of the funded first grid.
