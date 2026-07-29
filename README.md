# vibemax

A low-narration, management-by-exception response style for AI coding agents.

Most agents narrate everything: what they are about to do, what they just did, a
recap of the file they already wrote. You scroll past all of it to find the one line
that actually needed you. vibemax cuts the narration and keeps that line. The work
underneath stays at full effort - the agent just stops talking about the parts you
were never going to act on, and surfaces only what needs your attention: a question, a
caveat, an assumption it had to make, and a short result. Those four category names -
Questions, Caveats, Assumptions, Result - are plain words in [SKILL.md](SKILL.md), not
magic tokens: rename them to whatever your own vocabulary says.

It optimizes for your attention, not the token bill. Any tokens it saves are a side
effect; the point is that what you read is all signal.

It is a selection rule, not a compression rule. Nothing gets shorter by dropping
caveats or uncertainty - what was verified versus what was inferred stays in. It gets
shorter by dropping the play-by-play. The reasoning and evidence behind these claims -
the design argument, the battle-test protocol, the economics - are in
[DESIGN.md](DESIGN.md). The launch story, with session receipts and the
cost-composition chart, is the blog post: [Your Agent's Output Style Won't Save You
Money](https://totallydomo.github.io/posts/vibemax-output-style-wont-save-you-money/).

## Quieter is not more autonomous

vibemax changes how much the agent says, not what it
is allowed to do. Every confirmation it would normally ask for, it still asks.

## Install

Clone into your skills directory and invoke it by name:

    git clone https://github.com/TotallyDomo/vibemax ~/.claude/skills/vibemax

For a single project, clone into that project's `.claude/skills/` instead.

## Make it default

Both routes are plain text you add to your own config - this repo ships no code.

**CLAUDE.md import - start here.** Add one line to `~/.claude/CLAUDE.md`:

    @~/.claude/skills/vibemax/SKILL.md

The contract (under 400 input tokens) loads once per session and rides the prompt cache from
there. The tokenomics work out: Claude prices output at 5x input and cached input at
0.1x input, so the cached contract carries for the equivalent of roughly 7-10 output
tokens per request - about one narrated sentence. In our own transcripts, switching it
on cut visible narration by 9-14 output tokens per request, so the style pays for
itself with a small bonus. Attention is still the point; the token delta is a rounding
error either way.

**Hook variant - strongest adherence in very long sessions.** A `UserPromptSubmit`
hook re-injects the style on every prompt, so it never fades as the context grows. The
naive form - `cat` the contract on each prompt - pays for a fresh copy every time,
which costs more than the narration it saves. What we run instead: the full contract
on the session's first prompt, a one-line reminder after. As a script, saved wherever
you keep your own tooling (it is deliberately not part of this repo), e.g.
`~/.claude/vibemax-hook.sh`:

    #!/bin/sh
    # Full contract on the session's first prompt, a one-line reminder after.
    session=$(sed -n 's/.*"session_id" *: *"\([^"]*\)".*/\1/p')
    marker="${TMPDIR:-/tmp}/vibemax-seen-$session"
    if [ ! -f "$marker" ]; then
      touch "$marker"
      cat "$HOME/.claude/skills/vibemax/SKILL.md"
    else
      echo "vibemax style remains in effect; the contract appeared earlier in this conversation."
    fi

Wired up in `~/.claude/settings.json`:

    {
      "hooks": {
        "UserPromptSubmit": [
          {"hooks": [{"type": "command", "command": "sh ~/.claude/vibemax-hook.sh"}]}
        ]
      }
    }

The hook receives the prompt event as JSON on stdin and keys a marker file off the
session id, so each conversation pays the contract's input cost once. (Hooks run under
a POSIX shell on Windows too - keep the forward slashes.)

To turn it off mid-conversation, say so - "drop the vibemax style" works. Permanent
off is removing the line you added.

## Trust surface

The skill is markdown only - `SKILL.md` is all the agent ever loads. Nothing runs
at install time or use time, and nothing here fetches or sends anything anywhere.
`benchmarks/` holds the A/B harness and its run records; it runs only when you run
it. (The per-request narration figures above are production telemetry, not harness
output - DESIGN.md keeps the two evidence sources apart.) The one script that runs on its own is CI's
`scripts/agent-config-guard.sh`, which checks that no stray agent config got
committed to this repo. The optional hook above is one you write yourself into
your own config; the skill ships no code.

## License

Released under the MIT License. See [LICENSE](LICENSE).
