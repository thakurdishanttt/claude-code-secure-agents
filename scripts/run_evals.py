#!/usr/bin/env python3
"""Run the kit against real tasks and grade the result with hidden tests.

For each task in evals/tasks/<name>/:
  repo/     starting code (copied to a scratch dir and git-initialised)
  task.md   the prompt, usually a /build request
  accept/   hidden acceptance tests, copied in only AFTER the agent finishes

The kit is installed into a throwaway HOME, Claude Code runs headless, then
the hidden tests run. A task passes only if every hidden test passes and the
run stays within its budget in evals/budgets.json.

Usage: python3 scripts/run_evals.py [--tasks a,b] [--runs N] [--jobs N] [--out results.json] [--kit DIR]
Needs: the `claude` CLI, authenticated (ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN), python3 with pytest.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "evals" / "tasks"
ALLOWED_TOOLS = [
    "Bash(python3 -m pytest:*)", "Bash(python -m pytest:*)", "Bash(pytest:*)",
    "Bash(git diff:*)", "Bash(git status:*)", "Bash(git log:*)", "Bash(git show:*)",
]
RUN_TIMEOUT = 1200


def sh(cmd: list[str], cwd: Path, env: dict | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def run_one(name: str, run: int, budget: dict, kit: Path) -> dict:
    task = TASKS / name
    result = {"task": name, "run": run, "passed": False, "problems": []}
    with tempfile.TemporaryDirectory(prefix=f"eval-{name}-") as tmp:
        home, work = Path(tmp) / "home", Path(tmp) / "work"
        home.mkdir()
        shutil.copytree(task / "repo", work)
        env = {**os.environ, "HOME": str(home), "CLAUDE_HOME": str(home / ".claude")}
        env.pop("CLAUDE_CONFIG_DIR", None)
        inst = sh(["bash", str(kit / "install.sh"), "--no-auto-update"], kit, env)
        if inst.returncode:
            result["problems"].append(f"install failed: {inst.stderr[-300:]}")
            return result
        for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                    ["git", "-c", "user.email=eval@local", "-c", "user.name=eval", "commit", "-qm", "start"]):
            sh(cmd, work)

        prompt = (task / "task.md").read_text(encoding="utf-8").strip()
        prompt += "\n\nThis is an unattended run: any plan is pre-approved, do not wait for approval, run every gate to the end."
        start = time.monotonic()
        try:
            p = sh(["claude", "-p", prompt, "--output-format", "json", "--permission-mode", "acceptEdits",
                    "--allowedTools", *ALLOWED_TOOLS], work, env, RUN_TIMEOUT)
            out = json.loads(p.stdout or "{}")
        except subprocess.TimeoutExpired:
            out = {}
            result["problems"].append(f"timed out after {RUN_TIMEOUT}s")
        except ValueError:
            out = {}
            result["problems"].append(f"claude returned no JSON: {p.stderr[-300:]}")
        result["seconds"] = round(time.monotonic() - start)
        result["cost_usd"] = round(float(out.get("total_cost_usd") or 0), 4)
        result["turns"] = out.get("num_turns")
        if out.get("is_error"):
            result["problems"].append(f"claude error: {str(out.get('result'))[:300]}")

        accept_dir = work / "tests"
        accept_dir.mkdir(exist_ok=True)
        for f in (task / "accept").iterdir():
            shutil.copy2(f, accept_dir / f.name)
        t = sh([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(accept_dir)], work, timeout=300)
        result["tests"] = (t.stdout.strip().splitlines() or ["no output"])[-1]
        if t.returncode:
            result["problems"].append(f"hidden tests failed: {result['tests']}")
        if result["cost_usd"] > budget["max_cost_usd"]:
            result["problems"].append(f"cost ${result['cost_usd']} > budget ${budget['max_cost_usd']}")
        if result["seconds"] > budget["max_seconds"]:
            result["problems"].append(f"{result['seconds']}s > budget {budget['max_seconds']}s")
        result["passed"] = not result["problems"]
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="", help="comma-separated task names (default: all)")
    ap.add_argument("--runs", type=int, default=1, help="runs per task")
    ap.add_argument("--jobs", type=int, default=3, help="runs in parallel")
    ap.add_argument("--out", default="", help="write JSON results here")
    ap.add_argument("--kit", default=str(ROOT), help="kit checkout to install (default: this repo)")
    args = ap.parse_args()

    if not shutil.which("claude"):
        print("claude CLI not found", file=sys.stderr)
        return 2
    budgets = json.loads((ROOT / "evals" / "budgets.json").read_text(encoding="utf-8"))
    names = [n for n in args.tasks.split(",") if n] or sorted(p.name for p in TASKS.iterdir() if p.is_dir())
    unknown = [n for n in names if n not in budgets]
    if unknown:
        print(f"no budget for: {unknown}", file=sys.stderr)
        return 2

    jobs = [(n, r) for n in names for r in range(1, args.runs + 1)]
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = list(pool.map(lambda j: run_one(j[0], j[1], budgets[j[0]], Path(args.kit).resolve()), jobs))

    print(f"{'task':<16} {'run':>3} {'result':<6} {'cost':>7} {'secs':>5}  tests / problems")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        detail = r.get("tests", "") if r["passed"] else "; ".join(r["problems"])
        print(f"{r['task']:<16} {r['run']:>3} {status:<6} {r.get('cost_usd', 0):>7.3f} {r.get('seconds', 0):>5}  {detail}")
    total = sum(r.get("cost_usd", 0) for r in results)
    passed = sum(r["passed"] for r in results)
    print(f"\n{passed}/{len(results)} passed, total cost ${total:.2f}")
    if args.out:
        Path(args.out).write_text(json.dumps({"results": results, "total_cost_usd": round(total, 4)}, indent=2) + "\n")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
