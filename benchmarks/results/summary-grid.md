# Benchmark summary: grid

## Visible output tokens per request (chars/4 estimate)

| model | task | n blind/vibemax | blind | vibemax | delta |
|---|---|---|---|---|---|
| fable | t1 | 5/5 | 382.5 | 191.6 | -190.9 |
| fable | t3 | 5/5 | 396.3 | 233.7 | -162.6 |
| fable | t5 | 5/5 | 689.7 | 419.2 | -270.5 |
| haiku | t1 | 10/10 | 308.3 | 161.4 | -146.9 |
| haiku | t3 | 10/10 | 212.8 | 106.1 | -106.7 |
| haiku | t5 | 10/10 | 341.1 | 228.7 | -112.3 |
| opus | t1 | 5/5 | 724.8 | 348.8 | -376.0 |
| opus | t3 | 5/5 | 574.8 | 358.0 | -216.8 |
| opus | t5 | 5/5 | 821.3 | 565.5 | -255.8 |
| sonnet | t1 | 10/10 | 221.5 | 219.2 | -2.3 |
| sonnet | t3 | 10/10 | 230.2 | 196.8 | -33.4 |
| sonnet | t5 | 10/10 | 490.7 | 374.5 | -116.1 |

## Pooled per model (all tasks, per-request, session-weighted)

| model | blind | vibemax | delta | 90% CI (bootstrap) | api-out blind | api-out vibemax |
|---|---|---|---|---|---|---|
| fable | 489.5 | 281.5 | -208.0 | [-287.0, -131.1] | 5348 | 3879 |
| haiku | 287.4 | 165.4 | -121.9 | [-150.9, -92.8] | 3537 | 3190 |
| opus | 706.9 | 424.1 | -282.9 | [-349.5, -215.6] | 10056 | 8048 |
| sonnet | 314.1 | 263.5 | -50.6 | [-104.2, 2.5] | 5526 | 5096 |

## Hidden-ask catch rate

| model | task | blind | vibemax |
|---|---|---|---|
| fable | t3 | 1.00 (n=5) | 1.00 (n=5) |
| fable | t5 | 1.00 (n=5) | 1.00 (n=5) |
| haiku | t3 | 1.00 (n=10) | 1.00 (n=10) |
| haiku | t5 | 1.00 (n=10) | 1.00 (n=10) |
| opus | t3 | 1.00 (n=5) | 1.00 (n=5) |
| opus | t5 | 1.00 (n=5) | 1.00 (n=5) |
| sonnet | t3 | 1.00 (n=10) | 1.00 (n=10) |
| sonnet | t5 | 1.00 (n=10) | 1.00 (n=10) |

## Gotcha surfacing rate

| model | task | blind | vibemax |
|---|---|---|---|
| fable | t3 | 0.40 (n=5) | 0.40 (n=5) |
| fable | t5 | 0.20 (n=5) | 1.00 (n=5) |
| haiku | t3 | 0.10 (n=10) | 0.10 (n=10) |
| haiku | t5 | 0.50 (n=10) | 0.50 (n=10) |
| opus | t3 | 1.00 (n=5) | 0.40 (n=5) |
| opus | t5 | 0.20 (n=5) | 0.20 (n=5) |
| sonnet | t3 | 0.20 (n=10) | 0.00 (n=10) |
| sonnet | t5 | 0.60 (n=10) | 0.50 (n=10) |

## Quality guardrails (grader, approximate)

| model | cond | task_completed mean (0-2) | report_quality mean (1-5) | graded n |
|---|---|---|---|---|
| fable | blind | 1.93 | 4.20 | 15 |
| fable | vibemax | 1.93 | 4.13 | 15 |
| haiku | blind | 1.93 | 3.70 | 30 |
| haiku | vibemax | 1.87 | 3.57 | 30 |
| opus | blind | 1.87 | 4.27 | 15 |
| opus | vibemax | 1.73 | 4.13 | 15 |
| sonnet | blind | 1.77 | 3.77 | 30 |
| sonnet | vibemax | 1.80 | 3.63 | 30 |

## Run accounting

- ok sessions: 180; failed rows: 3
- session cost (list-equivalent): $220.40; grader cost: $5.45
