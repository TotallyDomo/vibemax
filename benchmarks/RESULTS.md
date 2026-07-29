# Results - grid v1 (2026-07-28, final record)

All four model blocks and the grading pass finished: 180 ok sessions (3 infra
failures re-run clean), Haiku 4.5 and Sonnet 5 at n=10 per cell, Opus 4.8 and
Fable 5 at n=5. Full per-cell tables: `results/summary-grid.md`
(`python analyze.py --tag grid`).

These are the controlled A/B numbers for this repo. They are a separate
evidence source from the per-request narration figure quoted in the top-level
README, which is observational production telemetry; the two are not
interchangeable. One environment defect, disclosed below, biases this grid
*against* vibemax - so read each delta as a conservative floor rather than a
point estimate. A rerun under the corrected configuration would be expected
to show larger cuts, not smaller.

## The defect, once

The harness launched child sessions with a tool allowlist that omitted shell
execution, so every attempt to actually run something - verification commands
above all - was permission-denied: 168 of 180 sessions hit at least one
denial (the 12 clean ones: 10 Haiku, 2 Sonnet), spread across both arms and
all models. Reading rules that follow:

- Models cope differently. Haiku skips the denied step almost silently (~2.7
  denials per job); Sonnet retries and asks the scripted, unanswering user
  for approval (~7.4 per job, approval-asking text in 57/60 sessions); Opus
  and Fable rack up as many denials or more (~8.9 and ~7.5 per job) while
  begging less - by coping style they sit between Haiku and Sonnet, not by
  count. The Haiku block is the cleanest material in the grid.
- vibemax deliberately preserves questions, so approval-asking survives both
  arms and converges them: the bias understates the vibemax cut, worst for
  Sonnet. The Sonnet delta is reported for completeness and should not be
  quoted as an effect size.
- Task completion stayed flat across arms everywhere (quality guardrails
  below), so the broken environment degraded both conditions equally rather
  than one condition's work.

The "Run discipline" rules in README.md (full permissions inside the sandbox,
staged rollout, stop-on-anomaly) exist because of this run.

## Visible output tokens per request (chars/4, pooled per model)

| model | n/cell | blind | vibemax | delta | 90% CI (bootstrap) |
|---|---|---|---|---|---|
| Haiku 4.5 | 10 | 287 | 165 | -122 | [-151, -93] |
| Sonnet 5 | 10 | 314 | 264 | -51 | [-104, +3] (confounded, do not quote) |
| Opus 4.8 | 5 | 707 | 424 | -283 | [-350, -216] |
| Fable 5 | 5 | 490 | 282 | -208 | [-287, -131] |

Every per-cell delta is negative (Sonnet t1's -2 is the one near-zero). At
n=5 the Opus and Fable intervals are directional, not tight.

## Thinking decomposition (`thinking_decomp.py`)

Only Haiku exposes thinking text in stream-json; Sonnet/Opus/Fable emit
signature-only thinking blocks, so their thinking is estimated as the residual
`api_output - text_est - tool_use_est` (Haiku validates the method).

- **No thinking tax anywhere.** The narration vibemax suppresses is deleted,
  not displaced into hidden reasoning: thinking/residual deltas are flat to
  strongly negative in every cell except Haiku t1 (+85, sub-noise, the fixed
  per-report-overhead regime).
- Total API output tokens drop well beyond the visible cut on multi-turn
  cells: Haiku t3/t5 -0.6k/-0.7k per request, Fable -0.9k to -1.8k, Opus
  -1.3k to -2.7k, with api-turns-per-request flat or lower. The surplus is
  less hidden reasoning and leaner tool traffic, not dropped work - task
  completion scores are flat across conditions.

## Attention metrics (graded; confound caveat applies)

- **Hidden-ask catch rate: 1.00 in every cell, both arms, all models.** The
  planted asks were too easy; the metric has no discriminative power at this
  difficulty. Read as "no evidence of degradation" only; a harder version is
  future work.
- **Gotcha surfacing: no consistent direction at these n.** The two
  eye-catchers cut opposite ways - Fable t5 0.20 blind vs 1.00 vibemax (n=5),
  Opus t3 1.00 blind vs 0.40 vibemax (n=5) - and everything else is within
  noise of equal. Neither is quotable; both are listed so neither gets
  cherry-picked later.
- **Quality guardrails**: task_completed flat (largest gap 0.13 of 2, Opus,
  n=15/arm); report_quality consistently ~0.07-0.15 of 5 lower under vibemax
  in all four models - plausibly real (a grader rubric that rewards thorough
  narration would produce exactly this), worth one deliberate look in any
  future run.

## Amendments during the run

- Opus was reduced from n=10 to n=5 mid-run by a budget call, before any Opus
  grading or analysis (freeze.txt amendment 3).
- 3 Fable t5 sessions failed on exhausted rate-limit retries and were re-run
  clean later (infrastructure failure; permitted by the freeze rules).

## Cost

Sessions $225.58 at list API prices - Haiku $11.66, Sonnet $65.73, Opus
$61.48, Fable $86.72 (the Fable figure includes the three failed-and-retried
sessions) - plus $5.45 grading and $2.18 pilot: about $233 for the whole grid
by the harness's own per-row accounting. An independent repricing of the raw
transcripts, which also captures restarted jobs the harness never billed,
lands within a few percent of the same total.
