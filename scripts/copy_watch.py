#!/usr/bin/env python3
"""Find public forks and copies of this kit and the skills repo on GitHub.

Checks, all through the public GitHub REST API:
  1. forks of each watched repository
  2. repositories whose name, description or README matches our names
  3. code search for sentences that only exist in our files (catches copies
     uploaded without forking, once GitHub has indexed them)

Prints a Markdown report of findings not seen before and, with --issue,
posts it as a comment on one tracking issue (labelled `copy-watch`).
Findings already listed in earlier comments are not repeated.

  python3 scripts/copy_watch.py                     # report to stdout
  python3 scripts/copy_watch.py --issue             # also post to the tracking issue

Env: GH_TOKEN (writes the tracking issue; the workflow token is enough),
     SEARCH_TOKEN (optional, used for searches; code search needs a user token
     or fine-grained PAT), GITHUB_REPOSITORY (owner/repo for the tracking issue).
Read-only on GitHub except for the one tracking issue. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OWNER = "thakurdishanttt"
WATCHED = ["claude-code-secure-agents", "claude-secure-agents-skills"]
REPO_QUERIES = [
    # Quoted: unquoted names are split into words and match thousands of repos.
    '"claude-code-secure-agents" in:name,description,readme',
    '"claude-secure-agents-skills" in:name,description,readme',
    '"Thakur Dishant Kumar" in:readme,description',
]
# Sentences that appear only in our files. Exact-phrase code search.
MARKERS = {
    "kit: reviewer agent": "You are a Staff Application Security Engineer and code reviewer for",
    "kit: security standard": "Global standard for every project and every agent",
    "skill: secure-feature-build": "You are the engineering lead for this change",
    "skill: threat-model": "Write a threat model engineers can implement and reviewers can check",
    "skill: dependency-vetting": "Decide whether a dependency is safe to adopt",
    "skill: iac-security-review": "Review infrastructure and pipeline definitions the way a cloud security",
    "copyright": "Thakur Dishant Kumar",
}
LABEL = "copy-watch"
TITLE = "Copy watch: forks and copies of the kit and skills"
API = "https://api.github.com"


def call(path: str, params: dict | None = None, method: str = "GET", body: dict | None = None,
         search: bool = False):
    url = f"{API}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    token = (os.environ.get("SEARCH_TOKEN") if search else None) or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < 2:      # secondary rate limit on search
                time.sleep(30 * (attempt + 1))
                continue
            raise


def ours(full_name: str) -> bool:
    return full_name.split("/")[0].lower() == OWNER.lower()


def collect() -> tuple[dict[str, str], list[str]]:
    """Return {repo full_name: why found}, and warnings for checks that could not run."""
    found: dict[str, str] = {}
    warnings: list[str] = []

    def add(name: str, why: str) -> None:
        if not ours(name):
            found.setdefault(name, why)

    for repo in WATCHED:
        page = 1
        while True:
            forks = call(f"/repos/{OWNER}/{repo}/forks", {"per_page": 100, "page": page}, search=True)
            for f in forks:
                add(f["full_name"], f"fork of {repo}")
            if len(forks) < 100:
                break
            page += 1
    for q in REPO_QUERIES:
        for r in call("/search/repositories", {"q": q, "per_page": 50}, search=True)["items"]:
            add(r["full_name"], f"name, description or README mentions {q.split(' in:')[0]}")
        time.sleep(3)
    for label, phrase in MARKERS.items():
        try:
            res = call("/search/code", {"q": f'"{phrase}"', "per_page": 50}, search=True)
        except urllib.error.HTTPError as e:
            warnings.append(f"code search unavailable ({e.code}); set a fine-grained token as AUTOMATION_TOKEN")
            break
        for item in res["items"]:
            add(item["repository"]["full_name"], f"contains {label} text (`{item['path']}`)")
        time.sleep(7)                                       # code search: 10 requests/minute
    return found, warnings


def downloads() -> list[str]:
    rows = []
    for repo in WATCHED:
        for rel in call(f"/repos/{OWNER}/{repo}/releases", {"per_page": 5}):
            n = sum(a.get("download_count", 0) for a in rel.get("assets", []))
            rows.append(f"{repo} {rel['tag_name']}: {n} asset download(s)")
    return rows


def tracking_issue(repo: str) -> tuple[int | None, set[str]]:
    issues = call(f"/repos/{repo}/issues", {"labels": LABEL, "state": "all", "per_page": 1})
    if not issues:
        return None, set()
    num = issues[0]["number"]
    seen: set[str] = set()
    page = 1
    while True:
        comments = call(f"/repos/{repo}/issues/{num}/comments", {"per_page": 100, "page": page})
        for c in comments:
            seen |= set(re.findall(r"github\.com/([\w.-]+/[\w.-]+)\)", c.get("body") or ""))
        if len(comments) < 100:
            break
        page += 1
    return num, seen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", action="store_true", help="post new findings to the tracking issue")
    a = ap.parse_args()
    repo = os.environ.get("GITHUB_REPOSITORY", f"{OWNER}/{WATCHED[0]}")

    found, warnings = collect()
    num, seen = tracking_issue(repo) if a.issue else (None, set())
    new = {k: v for k, v in sorted(found.items()) if k not in seen}

    lines = [f"**{len(new)} new** · {len(found)} total found this run · {time.strftime('%Y-%m-%d')}", ""]
    if new:
        lines += ["| Repository | Why it was flagged |", "|---|---|"]
        lines += [f"| [{k}](https://github.com/{k}) | {v} |" for k, v in new.items()]
        lines += ["", "Check each one: a fork or copy is allowed for the Apache-2.0 kit and the MIT skills "
                  "if `LICENSE`, `NOTICE` and the copyright line are kept. Proprietary skills need a licence."]
    lines += ["", "Release downloads: " + "; ".join(downloads())]
    lines += [f"\n> {w}" for w in sorted(set(warnings))]
    report = "\n".join(lines)
    print(report)

    if a.issue and (new or warnings or num is None):
        if num is None:
            try:
                call(f"/repos/{repo}/labels", method="POST", body={"name": LABEL, "color": "5319e7"})
            except urllib.error.HTTPError:
                pass                                        # label already exists
            num = call(f"/repos/{repo}/issues", method="POST", body={
                "title": TITLE, "labels": [LABEL],
                "body": "Weekly report of public forks and copies (`.github/workflows/copy-watch.yml`). "
                        "New findings are posted as comments; repositories already listed are not repeated."})["number"]
        call(f"/repos/{repo}/issues/{num}/comments", method="POST", body={"body": report})
        if new:
            call(f"/repos/{repo}/issues/{num}", method="PATCH", body={"state": "open"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
