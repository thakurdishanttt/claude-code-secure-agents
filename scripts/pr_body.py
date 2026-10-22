#!/usr/bin/env python3
"""Build the auto-update PR body.

The gate verdict is written by the pipeline and comes first. Bot-written text
(RUN_SUMMARY.md, reviewer findings) is quoted so it cannot pose as pipeline
output, and validator output is indented so it cannot break out of its block.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

MAX = 20_000


def read(path: str) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8", errors="replace")[:MAX] if p.is_file() else ""


def quote(text: str) -> str:
    return "\n".join("> " + line for line in text.strip().splitlines()) or "> (none)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--verdict", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--review", required=True)
    ap.add_argument("--validator", required=True)
    a = ap.parse_args()

    try:
        review = json.loads(read(a.review) or "{}")
    except ValueError:
        review = {}
    summary = "\n".join(read(a.summary).splitlines()[1:])
    findings = "\n".join(f"- {f}" for f in review.get("findings", []) if isinstance(f, str))
    validator = "\n".join("    " + l for l in read(a.validator).splitlines()) or "    (no output)"

    print(f"## Automated kit update → v{a.version}\n")
    print(f"**Release gate (set by the pipeline): {a.verdict}**\n")
    print("### What the update run changed (bot-written)\n")
    print(quote(summary) + "\n")
    print("### Independent reviewer (bot-written)\n")
    print(quote(str(review.get("summary", "")) + ("\n\n" + findings if findings else "")) + "\n")
    print("<details><summary>Validator output</summary>\n")
    print(validator + "\n")
    print("</details>\n")
    print("🤖 Generated with [Claude Code](https://claude.com/claude-code)")


if __name__ == "__main__":
    main()
