#!/usr/bin/env python3
"""Bump VERSION and stamp the CHANGELOG '## Unreleased' section.

New agent/command/standard files → minor bump; anything else → patch.
Prints `version=X.Y.Z` (for $GITHUB_OUTPUT).
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed", default="", help="space-separated changed paths")
    ap.add_argument("--floor", default="0.0.0", help="highest version already claimed (e.g. by an open PR)")
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--root", help="repository to bump (default: this script's repo)")
    args = ap.parse_args()
    global ROOT
    if args.root:
        ROOT = Path(args.root).resolve()

    def parse(v: str) -> tuple[int, int, int]:
        a, b, c = (int(x) for x in v.strip().split("."))
        return a, b, c

    major, minor, patch = max(parse((ROOT / "VERSION").read_text(encoding="utf-8")), parse(args.floor))
    # New agent/command/standard files (staged or untracked) → minor bump.
    added = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only", "--diff-filter=A", args.base, "--", "agents", "commands", "standards"],
        capture_output=True, text=True,
    ).stdout.split() + subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--others", "--exclude-standard", "agents", "commands", "standards"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    if added:
        minor, patch = minor + 1, 0
    else:
        patch += 1
    version = f"{major}.{minor}.{patch}"
    (ROOT / "VERSION").write_text(version + "\n", encoding="utf-8")

    cl = ROOT / "CHANGELOG.md"
    text = cl.read_text(encoding="utf-8") if cl.exists() else "# Changelog\n\n"
    heading = f"## v{version} — {dt.date.today().isoformat()} (automated)"
    if re.search(r"^## Unreleased\s*$", text, re.M):
        text = re.sub(r"^## Unreleased\s*$", heading, text, count=1, flags=re.M)
    else:
        files = ", ".join(sorted(set(args.changed.split()))) or "kit files"
        text = re.sub(r"^(# Changelog\s*\n)", rf"\1\n{heading}\n- Automated upstream sync ({files}).\n", text, count=1)
    cl.write_text(text, encoding="utf-8")
    print(f"version={version}")


if __name__ == "__main__":
    main()
