#!/usr/bin/env python3
"""Verify that the kit is installed correctly on this machine.

  python3 scripts/verify_install.py [--claude-home PATH] [--expect-version X.Y.Z]

Exit 0 = installed and wired up, 1 = something is missing. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ["agents/planner.md", "agents/researcher.md", "agents/coder.md", "agents/reviewer.md",
        "agents/cleaner.md", "commands/build.md", "standards/ai-security.md",
        "standards/ai-security-index.md", "hooks/prompt-reminder.txt"]


def hook_count(settings: dict, event: str, marker: str) -> int:
    return sum(
        1
        for entry in settings.get("hooks", {}).get(event, []) or []
        for h in entry.get("hooks", []) or []
        if marker in str(h.get("command", ""))
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claude-home", default=os.environ.get("CLAUDE_HOME", str(Path.home() / ".claude")))
    ap.add_argument("--expect-version")
    a = ap.parse_args()
    home = Path(a.claude_home)
    state = home / "enterprise-agents"
    ok, problems = [], []

    manifest = state / "manifest.txt"
    files = [l.strip() for l in manifest.read_text(encoding="utf-8").splitlines() if l.strip()] if manifest.exists() else []
    if not files:
        problems.append(f"no install manifest at {manifest} — run the installer")
    for rel in sorted(set(files) | set(CORE)):
        p = home / rel
        if rel.endswith(".ps1") and os.name != "nt" or rel.endswith(".sh") and os.name == "nt":
            continue
        if not p.is_file():
            problems.append(f"missing {p}")
        elif "__CLAUDE_HOME__" in p.read_text(encoding="utf-8", errors="replace"):
            problems.append(f"placeholder not substituted in {p}")
    if not any(x.startswith("missing") or x.startswith("placeholder") for x in problems):
        ok.append(f"{len(set(files) | set(CORE))} kit files present in {home}")

    md = home / "CLAUDE.md"
    if md.exists() and "BEGIN claude-enterprise-agents" in md.read_text(encoding="utf-8", errors="replace"):
        ok.append("global rules block present in CLAUDE.md")
    else:
        problems.append(f"global rules block missing from {md}")

    sp = home / "settings.json"
    try:
        settings = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    except ValueError as exc:
        settings = {}
        problems.append(f"{sp} is not valid JSON ({exc}) — Claude Code will ignore it")
    n = hook_count(settings, "UserPromptSubmit", "prompt-reminder.txt")
    if n == 1:
        ok.append("per-prompt rules hook installed")
    else:
        problems.append(f"expected 1 per-prompt rules hook, found {n}")
    auto_off = (state / "auto-update-disabled").exists()
    u = hook_count(settings, "SessionStart", "self-update")
    if auto_off:
        ok.append("auto-update: off")
        if u:
            problems.append("auto-update is disabled but its hook is still installed")
    elif u == 1 and (state / "src" / ".git").is_dir():
        ok.append("auto-update: on (background, at most once a day)")
    elif u == 1:
        problems.append("auto-update hook installed but no release checkout in "
                        f"{state / 'src'} (git missing or repo unreachable at install time)")
    else:
        problems.append(f"expected 1 self-update hook, found {u}")

    version = (state / "VERSION").read_text(encoding="utf-8").strip() if (state / "VERSION").exists() else "?"
    expect = a.expect_version or ((ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else None)
    def vt(v: str) -> tuple:
        try:
            return tuple(int(x) for x in v.split("."))
        except ValueError:
            return (0,)
    if expect and version == "?":
        problems.append("installed version unknown")
    elif expect and vt(version) < vt(expect):
        problems.append(f"installed version {version} is older than this checkout ({expect})")
    elif expect and vt(version) > vt(expect):
        ok.append(f"version {version} (newer than this checkout, {expect}; kept)")
    else:
        ok.append(f"version {version}")

    for line in ok:
        print(f"OK    {line}")
    for line in problems:
        print(f"FAIL  {line}")
    print("\nPASS — restart Claude Code to load it." if not problems else f"\nFAIL: {len(problems)} problem(s)")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
