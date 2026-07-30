# vibemax: design notes

The README says what vibemax is and how to run it; SKILL.md is the contract itself. This
document is the why: the problem, the design position, the evidence, and the limits. It is
written for someone deciding whether the idea is sound, not just whether the install works.
The narrative version, with the session receipts, is the launch post:
[Your Agent's Output Style Won't Save You
Money](https://totallydomo.github.io/posts/vibemax-output-style-wont-save-you-money/).

## The problem

An agentic coding session inverts the old chat ratio. The agent takes dozens of actions per
user turn - reads, edits, builds, test runs - and by default it narrates all of them: what
it is about to do, what it is doing, what it just did, and a recap of what it already showed
you. The human supervising the session needs almost none of that. What they need from a turn
is small: did anything go wrong, is a decision pending, what changed, and how much of that
was verified rather than assumed.

The cost of the surplus is not the tokens. In our own transcripts, visible narration is
under one percent of a session's token bill - tool payloads and reasoning dominate by orders
of magnitude. The cost is attention. The one question the agent asked sits in the middle of
paragraph four; the caveat that mattered is wedged between two recaps. The supervisor either
reads everything (slow) or skims (and misses the ask). A buried question stalls the turn. A
skimmed-past caveat quietly transfers risk to the person who never saw it.

## The goal

Optimize what the human reads, not what the model emits. vibemax borrows management by
exception from operations practice: routine execution goes unreported, exceptions get
surfaced. Applied to an agent's chat output, that means the play-by-play goes away and four
kinds of content are guaranteed a place: questions, caveats, assumptions, and a short
result. Everything the user was never going to act on is noise; everything that is theirs
to decide, or that shifts what they believe about the work, is signal. The work underneath
- the reasoning, the checks, the confirmations - is explicitly unchanged.

Token savings are not a goal. Whatever vibemax saves in output tokens is a side effect,
and it is small (measured below). A style pitched on token savings optimizes the wrong
axis, and the next section is about the failure mode that follows from that pitch.

## Selection, not compression

The viral style skill of mid-2026 - caveman - is a compression rule: answer in clipped
caveman-speak, drop the grammar, drop the filler, drop the hedging, and watch output tokens
fall. It shortens every sentence and keeps (roughly) all of them.

vibemax is the counter-position: a selection rule. It drops entire categories of output -
the pre-tool announcements, the progress pings, the recaps, the pleasantries - and keeps
the surviving sentences whole: full grammar, and every marker of uncertainty intact.

The distinction sounds cosmetic. It is not, because of what word-level compression deletes.
"Probably", "I didn't verify this", "assuming the config is standard" are not filler - they
are the agent's calibration surface, the only channel through which the model's uncertainty
reaches the person deciding what to double-check. Deleting a hedge does not remove the
uncertainty; it hides it. Compressed output reads more confident than the model actually
is, and the reader cannot tell audited claims from guesses. That is the expensive failure:
not longer scrolling, but misplaced trust.

The two rules also fail differently. Compression fails silently - a wrong claim arrives
fluent, short, and confident. Selection fails loudly: if vibemax drops something the user
needed, the user notices the hole and asks, which makes the failure observable and the
style testable. The battle-test protocol below is built directly on that property.

### Why not just "be concise"

A one-line brevity instruction delegates the cut to the model, and the model cuts by
statistical resemblance to filler. Hedges, assumptions, and embedded questions look like
filler; they are disproportionately what disappears. vibemax instead enumerates both lists
- what to suppress, what must always surface - so brevity never gets to negotiate against
the safety-relevant content. That asymmetry is the whole design: the contract is a
whitelist of what may be cut, not a mandate to be short.

## The four categories

The surface-by-exception list is exactly the content whose omission transfers risk from
the agent to the human:

- **Questions** - genuine forks that belong to the user. A dropped question does not
  disappear; it becomes a decision the agent made implicitly.
- **Caveats** - risks, surprises, contradictions with what the user believes. The item
  most likely to be skimmed past in narrated output, and the reason attention is the
  scarce resource worth optimizing.
- **Assumptions** - defaults chosen under ambiguity. Cheap to state, expensive to
  discover later.
- **Result** - what changed, and what was verified versus inferred. Kept even on success:
  in a domain the user cannot eyeball, the result line is their only checkpoint.

Nothing else is guaranteed airtime, and these four always are.

## The autonomy invariant

The predictable misreading of "low-narration" is "low-friction": an agent that talks less
might also ask less, confirm less, and act more freely. The contract pins this shut in its
own section: quieter is not more autonomous. Every confirmation the agent would normally
ask for, it still asks; no check is skipped because reporting got terse.

This section is load-bearing, and it is the one part of the contract that must never be
trimmed or paraphrased away. A model improvising a "hands-off style" from the description
alone could plausibly drift toward fewer confirmations; the explicit invariant is what
makes the style safe to hand to an agent unsupervised. Any fork of this contract should
keep it verbatim.

## Why the contract stays small

The contract is always-loaded text: it is paid for in every session (input tokens) and it
competes with the actual task for the model's instruction-following attention. Both costs
scale with size, so the body has a hard ceiling of about 400 tokens; the shipped version
measures about 330 (about 400 with frontmatter).

Keeping it there is active work, because this kind of contract grows under maintenance.
Twice during internal use, making the output terser required adding rules - suppression has
to be enumerated, and each newly noticed ceremony (structural scaffolding, ritualized
result blocks) needs its own line. Our in-house descendant of this contract, which carries
local workflow rules and a structured report grammar on top of the core, has grown to
roughly three to four times this size. v1 deliberately publishes the small, battle-tested
core and not that superstructure; the report-grammar layer may become a later version once
it has earned its tokens.

## Battle test: protocol and results

The style ran as a lived-usage experiment on the author's daily agent sessions before
publishing. Protocol, opt-in phase:

- **Human-triggered only.** The style was applied only when the user explicitly invoked
  it. The agent never self-selected it during the test - self-selection would contaminate
  the sample with the agent's own judgment of when the style looks good.
- **Routine, well-scoped tasks only** - not exploratory design discussions, where
  narration is the user's steering visibility and suppressing it would be wrong on
  purpose.
- **Failure definition.** A miss is any styled response after which the user had to ask
  "wait, what did you do?" or "what happened?" - i.e. the report failed its one job.
  Every miss gets logged, one line each.
- **Pass bar:** 10-15 tagged responses with zero misses.

Result: across about two and a half weeks of daily opt-in use (2026-07-01 to 2026-07-18),
the tagged responses cleared the bar with zero information misses, and the style was
promoted to the default for all of the author's sessions. The published SKILL.md body is a
genericized fork of exactly the contract that ran this test - local workflow references
stripped, the four categories and both guards intact (one later label rename: the
category tested as Gotchas ships as Caveats).

After promotion, a heavier descendant of the same core ran default-on for 60+ sessions
over the following five days. A transcript sweep across all of them - probing for miss
phrasings ("wait, what did you do", "you missed", "more detail", "too terse") and for the
one-word opt-out - found zero live complaints and zero opt-outs. Revealed preference, for
what it is worth: turning it off cost one word, and it was never used.

Caveats, stated plainly: this is n=1 (the author), it is a self-experiment, and a phrase
sweep catches the complaint phrasings it probes for, not misses absorbed silently. It is
strong evidence that the style loses nothing in daily expert use; it is not a controlled
study. The controlled comparison is planned below.

## Token economics

Reported for honesty, not as a pitch. The contract costs about 400 input tokens once per
session and then rides the prompt cache. At current pricing - cached input around 0.1x the
input rate, output around 5x - carrying it costs the equivalent of roughly 7-10 output
tokens per request. Measured across about 28,000 requests in our own transcripts, enabling
the style cut visible output by 9-14 tokens per request, varying by model.

Comparing those two figures directly understates the saving, because they are not priced
the same way. The 7-10 already includes the contract's cache tail - it is re-read on every
request. A suppressed narration token has a tail too: it would have been written into the
cache once (2x input at the one-hour TTL) and then re-read on every remaining turn of the
session (0.1x each), so its lifetime price sits above the 5x face output rate. How far
above depends on where in the session it was emitted - roughly 1.6x face on the first of
twelve turns, 2.4x at fifty turns, 3.4x at a hundred - and mid-task narration is emitted
early, which is the worst position there is. A closing report, emitted last, costs face
value exactly, though in an interactive session it is not really last. Priced
symmetrically, the 9-14 tokens saved are worth nearer 14-21 output-token-equivalents per
request.

One item is left out of the 7-10 and pulls the other way: the contract's own one-time cache
write costs 400 tokens at 2x input, which on a cold prefix adds roughly as much again once
amortized over a session's API turns. In our own sessions the prefix is usually already
warm from the previous one, so the read-only figure holds; a cold start pays it.

Net: positive but small, and a rounding error of the bill in either direction. If token
spend is the problem you are solving, prune tool payloads; a response style is the wrong
lever.

## The controlled comparison

The lived-usage evidence is observational, so a scripted A/B harness ran a first
controlled grid (2026-07-28): two arms - no style versus vibemax - across three scripted
tasks, two of them carrying a planted gotcha and a hidden ask (the third is a routine
control), on four Claude models. The paired
design exists so the attention claims and the token claims come from the same runs. The
harness, the run records, and the measured numbers live in [benchmarks/](benchmarks/);
`benchmarks/RESULTS.md` is the record, including the one harness defect that run
disclosed and the conservative reading rules it forces. The remaining arms of the
original plan - a compression style and a bare "be concise" one-liner - are future work,
listed as such in `benchmarks/README.md`.

## Limitations

- **Wrong tool for discussions.** In design and exploration sessions, narration is how
  the user steers; vibemax targets execution-shaped work, and the battle test excluded
  discussion sessions by design.
- **Adherence fades with context.** Like any style instruction, it weakens over very long
  sessions unless re-injected; the README's hook variant exists for that case.
- **Assumes a reading supervisor.** The style reallocates attention; an unattended
  pipeline with no human reading the output gains nothing from it.
- **Evidence base.** The lived-usage numbers come from one user's transcripts on one
  vendor's model family. The first controlled grid in `benchmarks/` is the step past
  that; RESULTS.md states what it does and does not establish.
