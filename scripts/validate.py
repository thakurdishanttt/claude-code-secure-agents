#!/usr/bin/env python3
"""Guardrails for the agent kit. Run by humans, CI and the auto-update run.

  python3 scripts/validate.py                       # structural checks
  python3 scripts/validate.py --base origin/main    # + no-weakening checks vs base
  python3 scripts/validate.py --base origin/main --bot
                                                    # + restrict edits to kit paths

Exit code 0 = pass, 1 = fail. Stdlib only.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # overridable with --root (CI runs a pinned copy)
KIT_DIRS = ("agents", "commands", "standards", "hooks")
KIT_FILES = ("CLAUDE.global.md",)
# The auto-update bot may change only content. Installers and executable hooks
# run on every developer machine, so changes to them are reserved for humans.
BOT_ALLOWED = (
    "agents/", "commands/", "standards/", "hooks/prompt-reminder.txt", "CLAUDE.global.md",
    "README.md", "INTEGRATION.md", "CHANGELOG.md",
)
BOT_SCRATCH = {"UPSTREAM_REPORT.md", "RUN_SUMMARY.md", "validate.txt", "review1.json", "review.json"}
EXECUTABLE_FILES = ("install.sh", "install.ps1", "hooks/self-update.sh", "hooks/self-update.ps1")
WEAKENERS = re.compile(
    r"\b(unless|except|optional(ly)?|if (needed|possible|practical|feasible)|where (possible|practical)|"
    r"should|may|might|can be skipped|when convenient|try to|ideally|recommended|"
    r"in production|in prod|for production|in staging|by default)\b", re.I)
# Words that, when ADDED to rule-bearing files, carve exceptions out of rules.
EXCEPTION_TERMS = re.compile(
    r"\b(unless|except|exception|exempt(ed|ion)?|override[sd]?|does not apply|do not apply|not required|"
    r"optional(ly)?|can be (skipped|ignored|relaxed)|if (needed|possible|practical|feasible)|"
    r"where (possible|practical)|ideally|best[- ]effort|in production only|outside production|"
    r"for (tests?|test fixtures|demos?|prototypes?))\b", re.I)
RULE_FILES = ("standards/", "agents/", "commands/", "CLAUDE.global.md", "hooks/prompt-reminder.txt")
FRONTMATTER_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*:( .*)?|\s+- .*|\s*)$")
PERMISSION_KEYS = {"mcpServers", "hooks", "permissionMode", "allowed-tools", "allowedTools", "skills"}
CORE_AGENTS = {"planner", "researcher", "coder", "reviewer", "cleaner"}
READ_ONLY_AGENTS = {"planner", "researcher", "reviewer"}
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
MODEL_ALIASES = {"sonnet", "opus", "haiku", "fable", "inherit"}
NORMATIVE = re.compile(r"\b(MUST|NEVER|Never|Forbidden|Do NOT|do NOT|MUST NOT|Blocked|BLOCK)\b")
SIMILARITY_FLOOR = 0.72
REMINDER_MAX = 1200
SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
DANGEROUS = [
    (re.compile(r"bypassPermissions"), "bypassPermissions is forbidden in the kit"),
    (re.compile(r"--dangerously-skip-permissions"), "--dangerously-skip-permissions is forbidden in the kit"),
    (re.compile(r"(curl|wget|iwr|Invoke-WebRequest)[^\n|]*\|\s*(ba)?sh|\|\s*iex\b", re.I), "pipe-to-shell download"),
]
HARDCODED_PATH = re.compile(r"(/Users/[A-Za-z]|/home/[A-Za-z]|[A-Z]:\\\\?Users\\\\)")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def kit_paths() -> list[Path]:
    out: list[Path] = []
    for d in KIT_DIRS:
        out += sorted(p for p in (ROOT / d).rglob("*") if p.is_file())
    out += [ROOT / f for f in KIT_FILES if (ROOT / f).exists()]
    return [p for p in out if not p.is_symlink()]


def scanned_paths() -> list[Path]:
    return kit_paths() + [ROOT / f for f in EXECUTABLE_FILES if (ROOT / f).exists()]


def frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fm: dict[str, str] = {}
    key = None
    for line in text[4:end].splitlines():
        if not FRONTMATTER_LINE.match(line):
            fm.setdefault("__invalid__", line)
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2).strip()
        elif key and line.strip().startswith("- "):
            fm[key] = (fm[key] + ", " if fm[key] else "") + line.strip()[2:].strip()
    return fm


def split_list(v: str) -> set[str]:
    v = v.strip().strip("[]")
    return {re.sub(r"\(.*\)$", "", t.strip().strip("'\"")) for t in v.split(",") if t.strip()}


# ------------------------------------------------------------- structural
def check_agents() -> None:
    files = {p.stem: p for p in (ROOT / "agents").glob("*.md") if not p.is_symlink()}
    for missing in sorted(CORE_AGENTS - files.keys()):
        err(f"agents/{missing}.md: core agent missing")
    for name, path in files.items():
        text = path.read_text(encoding="utf-8")
        fm = frontmatter(text)
        rel = path.relative_to(ROOT)
        if fm is None:
            err(f"{rel}: missing or malformed YAML frontmatter")
            continue
        if "__invalid__" in fm:
            err(f"{rel}: unsupported frontmatter line (use plain `key: value` / `- item`): {fm['__invalid__'][:80]}")
        if fm.get("name") != name:
            err(f"{rel}: frontmatter name '{fm.get('name')}' must equal file name '{name}'")
        if ":" in fm.get("name", "") or fm.get("name", "").startswith("-"):
            err(f"{rel}: invalid agent name")
        if len(fm.get("description", "")) < 20:
            err(f"{rel}: description missing or too short")
        model = fm.get("model")
        if model and model not in MODEL_ALIASES and not re.fullmatch(r"claude-[a-z0-9.-]+", model):
            err(f"{rel}: unknown model '{model}'")
        if fm.get("permissionMode") == "bypassPermissions":
            err(f"{rel}: permissionMode bypassPermissions is forbidden")
        if name in READ_ONLY_AGENTS:
            tools = split_list(fm.get("tools", ""))
            if not fm.get("tools"):
                err(f"{rel}: read-only agent must declare an explicit tools list")
            if tools & WRITE_TOOLS:
                err(f"{rel}: read-only agent must not have {sorted(tools & WRITE_TOOLS)}")
        if "__CLAUDE_HOME__/standards/ai-security.md" not in text:
            err(f"{rel}: must reference __CLAUDE_HOME__/standards/ai-security.md")
        if len(text.splitlines()) < 10:
            err(f"{rel}: suspiciously short agent body")


def check_commands() -> None:
    for path in (ROOT / "commands").glob("*.md"):
        if path.is_symlink():
            continue
        fm = frontmatter(path.read_text(encoding="utf-8"))
        if fm is None or not fm.get("description"):
            err(f"{path.relative_to(ROOT)}: frontmatter with description required")
        elif "__invalid__" in fm:
            err(f"{path.relative_to(ROOT)}: unsupported frontmatter line: {fm['__invalid__'][:80]}")
    if not (ROOT / "commands/build.md").exists():
        err("commands/build.md: /build orchestrator missing")


def check_symlinks() -> None:
    for d in (*KIT_DIRS, "scripts"):
        for p in (ROOT / d).rglob("*"):
            if p.is_symlink():
                err(f"{p.relative_to(ROOT)}: symlinks are not allowed in the kit")
    for f in (*KIT_FILES, *EXECUTABLE_FILES):
        if (ROOT / f).is_symlink():
            err(f"{f}: symlinks are not allowed in the kit")


def check_kit_text() -> None:
    for path in scanned_paths():
        rel = path.relative_to(ROOT)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            err(f"{rel}: not valid UTF-8")
            continue
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                err(f"{rel}: looks like a secret ({pat.pattern[:20]}…)")
        for pat, why in DANGEROUS:
            if pat.search(text):
                err(f"{rel}: {why}")
        if HARDCODED_PATH.search(text):
            err(f"{rel}: hard-coded user path; use __CLAUDE_HOME__")
    reminder = ROOT / "hooks/prompt-reminder.txt"
    if not reminder.exists():
        err("hooks/prompt-reminder.txt missing")
    elif len(reminder.read_text(encoding="utf-8")) > REMINDER_MAX:
        err(f"hooks/prompt-reminder.txt longer than {REMINDER_MAX} chars (it is added to every prompt)")
    g = (ROOT / "CLAUDE.global.md").read_text(encoding="utf-8")
    if "<!-- BEGIN claude-enterprise-agents -->" not in g or "<!-- END claude-enterprise-agents -->" not in g:
        err("CLAUDE.global.md: BEGIN/END markers required (installers replace the block by them)")
    std = (ROOT / "standards/ai-security.md").read_text(encoding="utf-8")
    for sev in ("Critical", "High"):
        if not re.search(rf"\*\*{sev}\*\*[^\n]*\|\s*Blocked\s*\|", std):
            err(f"standards/ai-security.md: severity '{sev}' must stay 'Blocked'")


def check_installers() -> None:
    sh = ROOT / "install.sh"
    r = subprocess.run(["bash", "-n", str(sh)], capture_output=True, text=True)
    if r.returncode:
        err(f"install.sh: bash syntax error: {r.stderr.strip()[:300]}")
    if shutil.which("shellcheck"):
        r = subprocess.run(["shellcheck", "-S", "error", str(sh), str(ROOT / "hooks/self-update.sh")],
                           capture_output=True, text=True)
        if r.returncode:
            err(f"shellcheck errors:\n{r.stdout.strip()[:1500]}")
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if pwsh:
        for ps in ("install.ps1", "hooks/self-update.ps1"):
            cmd = ("$e=$null;[System.Management.Automation.Language.Parser]::ParseFile("
                   f"'{ROOT / ps}',[ref]$null,[ref]$e)|Out-Null;if($e){{$e|%{{$_.Message}};exit 1}}")
            r = subprocess.run([pwsh, "-NoProfile", "-Command", cmd], capture_output=True, text=True)
            if r.returncode:
                err(f"{ps}: PowerShell parse errors: {r.stdout.strip()[:500]}")
    else:
        warnings.append("pwsh not found: PowerShell scripts not parsed")
    for f in ("install.sh", "install.ps1"):
        text = (ROOT / f).read_text(encoding="utf-8")
        for needed in ("UserPromptSubmit", "SessionStart", "prompt-reminder.txt", "self-update"):
            if needed not in text:
                err(f"{f}: must install '{needed}'")
    for f in (".github/automation/sources.json",):
        try:
            cfg = json.loads((ROOT / f).read_text(encoding="utf-8"))
            for s in cfg["sources"]:
                if "url" in s and not s["url"].startswith("https://"):
                    err(f"{f}: {s['id']} must use https")
        except (OSError, ValueError, KeyError) as exc:
            err(f"{f}: invalid ({exc})")
    v = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        err("VERSION must be MAJOR.MINOR.PATCH")


# ------------------------------------------------------------- vs base
def git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout


def norm(s: str) -> str:
    return re.sub(r"[\s`*_>#|-]+", " ", s).strip().lower()


def check_against_base(base: str, bot: bool) -> None:
    try:
        changed = [l for l in git("diff", "--name-only", base, "--").splitlines() if l]
        changed += [l for l in git("ls-files", "--others", "--exclude-standard").splitlines() if l]
    except RuntimeError as exc:
        err(f"cannot diff against {base}: {exc}")
        return
    if bot:
        for f in sorted(set(changed)):
            if not f.startswith(BOT_ALLOWED):
                err(f"{f}: the auto-update run may not modify this path")
        # Ignored files too: nothing may hide under .gitignore except known scratch files.
        ignored = git("status", "--porcelain", "--ignored", "--untracked-files=all").splitlines()
        for l in ignored:
            if l.startswith("!! "):
                path = l[3:].strip()
                if path not in BOT_SCRATCH and not path.startswith("__pycache__") and "/__pycache__/" not in path:
                    err(f"{path}: unexpected ignored file created during the auto-update run")
        # Lines added to rule-bearing files may not carve exceptions out of rules.
        for f in sorted(set(changed)):
            if not f.startswith(RULE_FILES) or not (ROOT / f).is_file() or (ROOT / f).is_symlink():
                continue
            try:
                before = git("show", f"{base}:{f}").splitlines()
            except RuntimeError:
                before = []
            after = (ROOT / f).read_text(encoding="utf-8").splitlines()
            for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, before, after).get_opcodes():
                if op not in ("insert", "replace"):
                    continue
                if op == "insert":
                    added = after[j1:j2]
                else:  # only the words this edit introduced
                    ow, nw = " ".join(before[i1:i2]).split(), " ".join(after[j1:j2]).split()
                    added = [" ".join(nw[b1:b2]) for o, _x, _y, b1, b2 in
                             difflib.SequenceMatcher(None, ow, nw).get_opcodes() if o in ("insert", "replace")]
                for line in added:
                    m = EXCEPTION_TERMS.search(line)
                    if m:
                        err(f"{f}: added text contains exception wording '{m.group(0)}' "
                            f"(needs a human): {line.strip()[:120]}")
        # Permission-bearing frontmatter may not be added, and disallowedTools may not shrink.
        for kind in ("agents", "commands"):
            for p in sorted((ROOT / kind).glob("*.md")):
                if p.is_symlink():
                    continue
                rel = f"{kind}/{p.name}"
                try:
                    old_fm = frontmatter(git("show", f"{base}:{rel}")) or {}
                except RuntimeError:
                    old_fm = {}
                new_fm = frontmatter(p.read_text(encoding="utf-8")) or {}
                for key in sorted(PERMISSION_KEYS & (new_fm.keys() - old_fm.keys())):
                    if not (key == "permissionMode" and new_fm[key] in ("plan", "default", "manual")):
                        err(f"{rel}: auto-update may not add permission-bearing key '{key}'")
                for key in PERMISSION_KEYS & new_fm.keys() & old_fm.keys():
                    if new_fm[key] != old_fm[key] and key != "skills":
                        err(f"{rel}: auto-update may not change '{key}'")
                lost = split_list(old_fm.get("disallowedTools", "")) - split_list(new_fm.get("disallowedTools", ""))
                if lost:
                    err(f"{rel}: disallowedTools entries removed: {sorted(lost)}")
                if old_fm.get("tools") and not new_fm.get("tools"):
                    err(f"{rel}: explicit tools list removed (agent would inherit all tools)")

    base_files = [l for l in git("ls-tree", "-r", "--name-only", base).splitlines()
                  if l.startswith(tuple(d + "/" for d in KIT_DIRS)) or l in KIT_FILES]
    for f in base_files:
        if not (ROOT / f).exists():
            if f.startswith(("agents/", "standards/")) or f in KIT_FILES:
                err(f"{f}: kit file removed (security content cannot be deleted)")
            continue
        try:
            old = git("show", f"{base}:{f}")
        except RuntimeError:
            continue
        # Rules are matched within the same file: a rule weakened in one file is not
        # excused by an intact copy elsewhere.
        file_lines = [norm(l) for l in (ROOT / f).read_text(encoding="utf-8").splitlines() if l.strip()]
        head_set = set(file_lines)
        head_normative = [l for l in file_lines if len(l) > 12]
        for line in old.splitlines():
            if not NORMATIVE.search(line) or len(line.strip()) < 12:
                continue
            n = norm(line)
            if n in head_set:
                continue
            # A reworded rule must stay similar AND keep its strength keywords (MUST, NEVER, ...).
            keywords = {k.lower() for k in NORMATIVE.findall(line)}
            candidates = [h for h in head_normative if keywords <= set(re.findall(r"[a-z]+", h))
                          or all(k in h for k in keywords)]
            scored = [(difflib.SequenceMatcher(None, n, h).ratio(), h) for h in candidates]
            best, match = max(scored, default=(0.0, ""))
            if best < SIMILARITY_FLOOR:
                err(f"{f}: security/safety rule removed, weakened or materially changed: {line.strip()[:160]}")
                continue
            # Look only at the words the new line inserted or replaced.
            old_w, new_w = n.split(), match.split()
            inserted = " ".join(
                " ".join(new_w[j1:j2])
                for op, _i1, _i2, j1, j2 in difflib.SequenceMatcher(None, old_w, new_w).get_opcodes()
                if op in ("insert", "replace")
            )
            added_weak = {m.group(0).lower() for m in WEAKENERS.finditer(inserted)}
            if added_weak:
                err(f"{f}: rule reworded with weakening terms {sorted(added_weak)}: {line.strip()[:120]}")

    def count_must(text: str) -> int:
        return len(re.findall(r"\bMUST\b", text))
    try:
        old_std = git("show", f"{base}:standards/ai-security.md")
        new_std = (ROOT / "standards/ai-security.md").read_text(encoding="utf-8")
        if count_must(new_std) < count_must(old_std):
            err(f"standards/ai-security.md: MUST rules dropped from {count_must(old_std)} to {count_must(new_std)}")
    except RuntimeError:
        pass

    for name in READ_ONLY_AGENTS:
        try:
            old_fm = frontmatter(git("show", f"{base}:agents/{name}.md")) or {}
        except RuntimeError:
            continue
        if not (ROOT / f"agents/{name}.md").exists():
            continue  # already reported as a removed kit file
        new_fm = frontmatter((ROOT / f"agents/{name}.md").read_text(encoding="utf-8")) or {}
        added = split_list(new_fm.get("tools", "")) - split_list(old_fm.get("tools", ""))
        if added and bot:
            err(f"agents/{name}.md: auto-update may not add tools to a read-only agent: {sorted(added)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="git ref to compare against (enables no-weakening checks)")
    ap.add_argument("--bot", action="store_true", help="also restrict changed paths to kit files")
    ap.add_argument("--root", help="repository to validate (default: this script's repo)")
    args = ap.parse_args()
    global ROOT
    if args.root:
        ROOT = Path(args.root).resolve()

    check_symlinks()
    check_agents()
    check_commands()
    check_kit_text()
    check_installers()
    if args.base:
        check_against_base(args.base, args.bot)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"FAIL  {e}")
    print(f"\n{'PASS' if not errors else 'FAIL'}: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
