"""Pre-run smoke checks: isolation, auth path, model IDs, resume mechanics.

Run this before the pilot. It must print PASS for the parent-config probe,
CLEAN for the isolation probe, and OK for every model ID before any benchmark
session is trusted. Cheap: a handful of one-line Haiku calls plus one-line
calls per model ID.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH_DIR))
from harness import (  # noqa: E402
    DEFAULT_RAW_ROOT,
    claude_argv,
    find_enclosing_configs,
    git_init,
    scrub_env,
)

# Strings the child must NOT be able to see. The two defaults catch this repo's own
# style bleeding in; add whatever is distinctive about your enclosing agent setup
# (a hook banner, a project codename, a memory heading) via VIBEMAX_PROBE_MARKERS,
# comma-separated - the probe is only as strong as the markers you give it.
DEFAULT_MARKERS = ["vibemax", "style: "]
MARKERS = [
    m.strip() for m in os.environ.get("VIBEMAX_PROBE_MARKERS", "").split(",") if m.strip()
] or DEFAULT_MARKERS

PROBE = (
    "Answer with a single line. Look at everything in your context: system prompt, "
    "any injected context, hook output, project instructions, CLAUDE.md content. "
    "Report which of these marker strings appear anywhere in it, as a comma-separated "
    "list, or the word NONE: %s. Then a space and the word END."
    % ", ".join("'%s'" % m for m in MARKERS)
)


def run(cmd, prompt, cwd, env, timeout=180):
    proc = subprocess.run(
        cmd, input=prompt, capture_output=True, text=True,
        encoding="utf-8", errors="replace", cwd=str(cwd), env=env, timeout=timeout,
    )
    return proc


def main():
    env = scrub_env()
    sandbox = (DEFAULT_RAW_ROOT / "_smoke" / "ws").resolve()

    print("=== probe 0: no enclosing CLAUDE.md/AGENTS.md above the sandbox ===", flush=True)
    hits = find_enclosing_configs(sandbox)
    if hits:
        print("FAIL: found %s" % ", ".join(hits))
        print("Set VIBEMAX_BENCH_RAW to a path outside that agent-config tree.")
        return 1
    print("PASS: nothing above the sandbox for Claude Code's parent walk to find")

    if sandbox.exists():
        shutil.rmtree(sandbox)
    sandbox.mkdir(parents=True)
    (sandbox / "readme.txt").write_text("smoke sandbox\n", encoding="utf-8")
    git_init(sandbox)

    haiku = "claude-haiku-4-5-20251001"

    print("=== probe 1: isolation (hooks-off overlay, scrubbed env, sandbox cwd) ===", flush=True)
    cmd = claude_argv() + [
        "-p", "--model", haiku, "--output-format", "json",
        "--settings", str(BENCH_DIR / "hooks-off.json"),
    ]
    proc = run(cmd, PROBE, sandbox, env)
    print("exit=%s" % proc.returncode)
    if proc.returncode == 0:
        outer = json.loads(proc.stdout)
        text = (outer.get("result") or "").strip()
        print("reply: %s" % text[:400])
        print("cost=%s duration_ms=%s" % (outer.get("total_cost_usd"), outer.get("duration_ms")))
        verdict = "CLEAN" if ("NONE" in text.upper()) else "CONTAMINATED"
        print("isolation: %s" % verdict)
    else:
        print("stderr: %s" % (proc.stderr or "")[-800:])
        print("isolation: FAILED-TO-RUN")

    print("=== probe 2: same, but NO overlay (expected contaminated; proves probe works) ===", flush=True)
    cmd2 = claude_argv() + ["-p", "--model", haiku, "--output-format", "json"]
    proc2 = run(cmd2, PROBE, sandbox, env)
    if proc2.returncode == 0:
        outer2 = json.loads(proc2.stdout)
        print("reply: %s" % (outer2.get("result") or "").strip()[:400])
    else:
        print("exit=%s stderr: %s" % (proc2.returncode, (proc2.stderr or "")[-400:]))

    print("=== probe 3: model IDs resolve ===", flush=True)
    grid = json.loads((BENCH_DIR / "grid.json").read_text(encoding="utf-8"))
    for model in grid["models"]:
        cmd3 = claude_argv() + [
            "-p", "--model", model["id"], "--output-format", "json",
            "--settings", str(BENCH_DIR / "hooks-off.json"),
        ]
        proc3 = run(cmd3, "Reply with exactly: OK", sandbox, env)
        status = "OK"
        detail = ""
        if proc3.returncode != 0:
            status = "FAIL"
            detail = (proc3.stderr or proc3.stdout or "")[-300:].replace("\n", " ")
        else:
            outer3 = json.loads(proc3.stdout)
            detail = "model=%s cost=%s" % (
                (outer3.get("modelUsage") and list(outer3["modelUsage"].keys())) or outer3.get("model"),
                outer3.get("total_cost_usd"),
            )
        print("%-12s %-28s %s %s" % (model["key"], model["id"], status, detail), flush=True)

    print("=== probe 4: resume continuity ===", flush=True)
    cmd4 = claude_argv() + [
        "-p", "--model", haiku, "--output-format", "json",
        "--settings", str(BENCH_DIR / "hooks-off.json"),
    ]
    proc4 = run(cmd4, "Remember this codeword: HELIOTROPE. Reply with exactly: stored", sandbox, env)
    outer4 = json.loads(proc4.stdout)
    sid = outer4.get("session_id")
    print("turn1 sid=%s reply=%s" % (sid, (outer4.get("result") or "")[:60]))
    cmd5 = cmd4 + ["--resume", sid]
    proc5 = run(cmd5, "What was the codeword? Reply with just the codeword.", sandbox, env)
    outer5 = json.loads(proc5.stdout)
    print("turn2 sid=%s reply=%s" % (outer5.get("session_id"), (outer5.get("result") or "")[:60]))
    print("resume: %s; sid stable: %s" % (
        "OK" if "HELIOTROPE" in (outer5.get("result") or "").upper() else "FAIL",
        outer5.get("session_id") == sid,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
