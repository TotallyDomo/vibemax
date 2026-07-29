# Benchmark summary: pilot

## Visible output tokens per request (chars/4 estimate)

| model | task | n blind/vibemax | blind | vibemax | delta |
|---|---|---|---|---|---|
| haiku | t1 | 2/2 | 365.0 | 61.1 | -303.9 |
| haiku | t3 | 2/2 | 206.0 | 129.2 | -76.8 |
| haiku | t5 | 2/2 | 339.0 | 217.6 | -121.4 |

## Pooled per model (all tasks, per-request, session-weighted)

| model | blind | vibemax | delta | 90% CI (bootstrap) | api-out blind | api-out vibemax |
|---|---|---|---|---|---|---|
| haiku | 303.3 | 136.0 | -167.4 | [-257.0, -83.4] | 3138 | 2861 |

## Hidden-ask catch rate

| model | task | blind | vibemax |
|---|---|---|---|
| haiku | t3 | 1.00 (n=2) | 1.00 (n=2) |
| haiku | t5 | 1.00 (n=2) | 1.00 (n=2) |

## Gotcha surfacing rate

| model | task | blind | vibemax |
|---|---|---|---|
| haiku | t3 | 0.50 (n=2) | 0.50 (n=2) |
| haiku | t5 | 1.00 (n=2) | 1.00 (n=2) |

## Quality guardrails (grader, approximate)

| model | cond | task_completed mean (0-2) | report_quality mean (1-5) | graded n |
|---|---|---|---|---|
| haiku | blind | 2.00 | 3.83 | 6 |
| haiku | vibemax | 1.83 | 3.50 | 6 |

## Run accounting

- ok sessions: 12; failed rows: 0
- session cost (list-equivalent): $2.18; grader cost: $0.32
