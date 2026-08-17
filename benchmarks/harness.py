"""A/B benchmark driver: blind vs vibemax, scripted multi-turn tasks, headless claude -p.

One job = one scripted session: a sandbox copy of tasks/template, 1..5 scripted user
turns driven through `claude -p` (first turn) and `claude -p --resume` (later turns),
stream-json captured per turn. The vibemax condition injects the contract via
--append-system-prompt, modeling the CLAUDE.md default-on install route.

Isolation: children run with a settings overlay that disables all hooks and a
scrubbed environment (no CLAUDE*/ANTHROPIC* vars); cwd is a git-inited sandbox
(for the diffstat check, not isolation - Claude Code walks parent directories
for CLAUDE.md/AGENTS.md regardless of git-init). Enclosing project config stays
out only when the raw root is outside every agent-config tree. The harness now
refuses a root with CLAUDE.md/AGENTS.md above it; the tempdir default normally
qualifies, but redirected tempdirs may not. Grid v1 ran with a raw root under
the author's agent tree; two transcripts show an enclosing CLAUDE.md bleeding
through. Both arms were affected equally, so that grid's A/B comparison stands.
Verify with smoke_probe.py before trusting runs - its live leakage check only
catches the marker strings it is given.

Re-runnable: completed job_ids in the results file are skipped, so a crashed run
resumes where it stopped. Raw stream-json per turn lands under the raw dir.
"""

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent

# Raw stream-json and the per-job sandboxes land here. Deliberately outside the
# repo so a sandbox (which gets its own git init) never lands in this worktree.
# Override with --raw-dir, or VIBEMAX_BENCH_RAW for the whole run.
DEFAULT_RAW_ROOT = Path(
    os.environ.get("VIBEMAX_BENCH_RAW") or (Path(tempfile.gettempdir()) / "vibemax-bench")
)


def find_enclosing_configs(path):
    """CLAUDE.md/AGENTS.md in any parent that a child session can walk."""
    hits = []
    for parent in path.parents:
        for name in ("CLAUDE.md", "AGENTS.md"):
            candidate = parent / name
            if candidate.exists():
                hits.append(str(candidate))
    return hits

RETRYABLE = re.compile(
    r"overloaded|rate.?limit|too many requests|\b429\b|\b5\d\d\b|timed? ?out"
    r"|econnreset|etimedout|socket hang up|fetch failed|network error|api error",
    re.I,
)
RESUME_FAIL = re.compile(
    r"no conversation|session.*not found|not found.*session|cannot resume|unknown session",
    re.I,
)

_print_lock = threading.Lock()
_results_lock = threading.Lock()
_cost_lock = threading.Lock()
_cum_cost = 0.0


def log(msg):
    with _print_lock:
        print(msg, flush=True)


def scrub_env():
    env = dict(os.environ)
    for key in list(env):
        upper = key.upper()
        if upper.startswith("CLAUDE") or upper.startswith("ANTHROPIC"):
            env.pop(key)
    return env


def claude_argv():
    exe = shutil.which("claude")
    if exe is None:
        sys.exit("claude CLI not found on PATH")
    if exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe]
    return [exe]


def load_contract():
    """SKILL.md body with frontmatter stripped, as checked into contract-vibemax.md."""
    path = BENCH_DIR / "contract-vibemax.md"
    return path.read_text(encoding="utf-8")


def build_turn_cmd(model_id, cond, resume_sid, contract_text):
    cmd = claude_argv() + [
        "-p",
        "--verbose",
        "--model", model_id,
        "--output-format", "stream-json",
        "--permission-mode", "bypassPermissions",
        "--settings", str(BENCH_DIR / "hooks-off.json"),
    ]
    if resume_sid:
        cmd += ["--resume", resume_sid]
    if cond == "vibemax":
        cmd += ["--append-system-prompt", contract_text]
    return cmd


def kill_tree(pid):
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        capture_output=True,
    )


def run_turn(cmd, prompt, cwd, env, timeout_s):
    start = time.time()
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=env,
    )
    try:
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout_s)
        timed_out = False
    except subprocess.TimeoutExpired:
        kill_tree(proc.pid)
        stdout, stderr = proc.communicate()
        timed_out = True
    return proc.returncode, stdout or "", stderr or "", time.time() - start, timed_out


def parse_stream(stdout_text):
    """Return (visible_text_blocks, result_event) from stream-json stdout."""
    visible = []
    seen = set()
    result = None
    for line in stdout_text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = event.get("type")
        if etype == "assistant":
            message = event.get("message") or {}
            mid = message.get("id")
            content = message.get("content") or []
            for idx, block in enumerate(content):
                if isinstance(block, dict) and block.get("type") == "text":
                    key = (mid, idx)
                    if key in seen:
                        continue
                    seen.add(key)
                    visible.append(block.get("text") or "")
        elif etype == "result":
            result = event
    return visible, result


def rmtree_force(path):
    """rmtree that survives Windows read-only files (git objects)."""
    def onexc(func, p, exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    shutil.rmtree(path, onexc=onexc)


def git_init(ws):
    base = ["git", "-C", str(ws), "-c", "user.email=bench@local", "-c", "user.name=bench"]
    subprocess.run(base[:3] + ["init", "-q"], capture_output=True)
    subprocess.run(base + ["add", "-A"], capture_output=True)
    subprocess.run(base + ["commit", "-q", "-m", "template baseline"], capture_output=True)


def git_diffstat(ws):
    proc = subprocess.run(
        ["git", "-C", str(ws), "diff", "--stat"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return (proc.stdout or "").strip()[-2000:]


def run_checks(task_def, ws, all_visible_text):
    checks = {}
    scoring = task_def.get("scoring") or {}
    hidden = scoring.get("hidden_ask")
    if hidden and hidden.get("file"):
        target = ws / hidden["file"]
        text = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        checks["hidden_ask_file_resolved"] = re.search(hidden["absent_pattern"], text) is None
    gotcha = scoring.get("gotcha")
    if gotcha and gotcha.get("regex"):
        checks["gotcha_regex"] = bool(re.search(gotcha["regex"], all_visible_text, re.I))
    attempted = []
    for check in scoring.get("attempt_checks") or []:
        target = ws / check["file"]
        if check.get("exists"):
            attempted.append(target.exists())
        elif check.get("present_pattern"):
            text = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
            attempted.append(re.search(check["present_pattern"], text) is not None)
    if attempted:
        checks["task_attempted"] = all(attempted)
    checks["conf_py_exists"] = (ws / "logsift" / "conf.py").exists()
    return checks


def turn_metrics(visible, result, duration, attempt):
    usage = (result or {}).get("usage") or {}
    visible_chars = sum(len(v) for v in visible)
    return {
        "visible_chars": visible_chars,
        "visible_est_tokens": round(visible_chars / 4.0, 1),
        "api_output_tokens": usage.get("output_tokens"),
        "api_input_tokens": usage.get("input_tokens"),
        "cache_read_tokens": usage.get("cache_read_input_tokens"),
        "cache_create_tokens": usage.get("cache_creation_input_tokens"),
        "cost_usd": (result or {}).get("total_cost_usd"),
        "num_api_turns": (result or {}).get("num_turns"),
        "duration_s": round(duration, 1),
        "attempts": attempt,
    }


def run_session(job, cfg, tasks, raw_root, env, contract_text, results_path):
    global _cum_cost
    task_def = tasks[job["task"]]
    job_dir = raw_root / job["job_id"]
    job_dir.mkdir(parents=True, exist_ok=True)
    last_error = None

    for restart in range(cfg["max_session_restarts"] + 1):
        ws = job_dir / ("ws" if restart == 0 else "ws%d" % restart)
        if ws.exists():
            rmtree_force(ws)
        if ws.exists():
            # still locked (e.g. an orphaned child holds it): use a fresh name
            ws = job_dir / ("ws-%d" % int(time.time() * 1000))
        shutil.copytree(BENCH_DIR / "tasks" / "template", ws)
        git_init(ws)

        sid = None
        turns = []
        visible_all = []
        failed = None
        restart_wanted = False
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        for turn_no, prompt in enumerate(task_def["turns"], 1):
            attempt = 0
            while True:
                attempt += 1
                cmd = build_turn_cmd(job["model_id"], job["cond"], sid, contract_text)
                code, stdout, stderr, duration, timed_out = run_turn(
                    cmd, prompt, ws, env, cfg["turn_timeout_s"]
                )
                visible, result = parse_stream(stdout)
                raw_path = job_dir / ("turn%d.jsonl" % turn_no)
                raw_path.write_text(stdout, encoding="utf-8")
                ok = (
                    code == 0
                    and not timed_out
                    and result is not None
                    and not result.get("is_error")
                )
                if ok:
                    sid = result.get("session_id") or sid
                    turns.append(turn_metrics(visible, result, duration, attempt))
                    visible_all.append("\n".join(visible))
                    break
                blob = " ".join(
                    [stderr[-2000:], stdout[-2000:], json.dumps(result or {})[:500]]
                )
                if sid and RESUME_FAIL.search(blob):
                    restart_wanted = True
                    last_error = "resume failed: " + blob[:300]
                    break
                if attempt <= cfg["max_turn_retries"] and (timed_out or RETRYABLE.search(blob)):
                    delay = min(120, 30 * attempt)
                    log("retry %s turn %d attempt %d in %ds" % (job["job_id"], turn_no, attempt, delay))
                    time.sleep(delay)
                    continue
                failed = "turn %d failed (code=%s timeout=%s): %s" % (
                    turn_no, code, timed_out, blob[:300]
                )
                break
            if failed or restart_wanted:
                break

        if restart_wanted and restart < cfg["max_session_restarts"]:
            log("restarting session %s (restart %d)" % (job["job_id"], restart + 1))
            continue

        all_visible_text = "\n\n".join(visible_all)
        status = "ok" if (failed is None and not restart_wanted and len(turns) == len(task_def["turns"])) else "failed"
        row = dict(job)
        row.update({
            "status": status,
            "error": failed or last_error if status == "failed" else None,
            "restarts": restart,
            "started_at": started,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "turns": turns,
            "n_requests": len(task_def["turns"]),
            "visible_chars_total": sum(t["visible_chars"] for t in turns),
            "visible_est_tokens_total": round(sum(t["visible_chars"] for t in turns) / 4.0, 1),
            "api_output_tokens_total": sum(t["api_output_tokens"] or 0 for t in turns),
            "cost_usd_total": round(sum(t["cost_usd"] or 0.0 for t in turns), 4),
            "session_id": sid,
            "ws_path": str(ws),
            "checks": run_checks(task_def, ws, all_visible_text),
            "git_diffstat": git_diffstat(ws),
            "visible_transcript": visible_all,
        })
        with _cost_lock:
            _cum_cost += row["cost_usd_total"]
            cum = _cum_cost
        with _results_lock:
            with open(results_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row) + "\n")
        log("done %s status=%s vis_tok=%.0f cost=%.2f cum=%.2f" % (
            job["job_id"], status, row["visible_est_tokens_total"], row["cost_usd_total"], cum
        ))
        return status

    return "failed"


def build_jobs(cfg):
    jobs = []
    for model in cfg["models"]:
        for task in cfg["tasks"]:
            for rep in range(1, cfg["n"] + 1):
                for cond in cfg["conditions"]:
                    jobs.append({
                        "job_id": "%s-%s-%s-%s-r%02d" % (cfg["tag"], model["key"], task, cond, rep),
                        "tag": cfg["tag"],
                        "model": model["key"],
                        "model_id": model["id"],
                        "task": task,
                        "cond": cond,
                        "rep": rep,
                    })
    return jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", required=True)
    parser.add_argument("--raw-dir", default=None,
                        help="raw output root (default $VIBEMAX_BENCH_RAW or <tempdir>/vibemax-bench, then /<tag>)")
    parser.add_argument("--results", default=None, help="results jsonl (default results/<tag>.jsonl)")
    parser.add_argument("--filter", default=None, help="regex on job_id; only matching jobs run")
    parser.add_argument("--concurrency", type=int, default=None)
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    tasks = json.loads((BENCH_DIR / "tasks" / "tasks.json").read_text(encoding="utf-8"))
    contract_text = load_contract()
    env = scrub_env()

    raw_root = (
        Path(args.raw_dir) if args.raw_dir else DEFAULT_RAW_ROOT / cfg["tag"]
    ).resolve()
    enclosing = find_enclosing_configs(raw_root / "_config_probe" / "ws")
    if enclosing:
        sys.exit(
            "unsafe raw root: Claude Code would load enclosing agent config:\n- "
            + "\n- ".join(enclosing)
            + "\nSet VIBEMAX_BENCH_RAW or --raw-dir to a path outside that tree."
        )
    raw_root.mkdir(parents=True, exist_ok=True)
    results_path = Path(args.results) if args.results else BENCH_DIR / "results" / (cfg["tag"] + ".jsonl")
    results_path.parent.mkdir(parents=True, exist_ok=True)

    done_ids = set()
    if results_path.exists():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("status") == "ok":
                done_ids.add(row.get("job_id"))

    jobs = build_jobs(cfg)
    if args.filter:
        jobs = [j for j in jobs if re.search(args.filter, j["job_id"])]
    pending = [j for j in jobs if j["job_id"] not in done_ids]
    log("jobs total=%d done=%d pending=%d cap=$%s" % (
        len(jobs), len(jobs) - len(pending), len(pending), cfg["cost_cap_usd"]
    ))

    concurrency = args.concurrency or cfg.get("concurrency", 3)
    failures = 0

    def worker(job):
        nonlocal failures
        with _cost_lock:
            over_cap = _cum_cost >= cfg["cost_cap_usd"]
        if over_cap:
            log("CAP reached, skipping %s" % job["job_id"])
            return
        try:
            status = run_session(job, cfg, tasks, raw_root, env, contract_text, results_path)
        except Exception as exc:  # a broken sandbox must not kill the whole run
            log("EXC %s: %r" % (job["job_id"], exc))
            status = "exception"
        if status != "ok":
            failures += 1

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(worker, pending))

    log("ALL DONE failures=%d cum_cost=%.2f" % (failures, _cum_cost))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
