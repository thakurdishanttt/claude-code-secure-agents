---
description: Install this agent kit on this machine for every project (runs the installer, verifies it, reports)
argument-hint: "[--no-auto-update]"
---
Install the claude-code-secure-agents kit globally on this machine, so it
applies to every project and every prompt. Do it end to end without asking
questions unless a step fails. Keep output short.

Options from the user: $ARGUMENTS
(`--no-auto-update` disables the background self-update; default is on.)

## 1. Pre-checks (one Bash call)
Run from the repository root:
```
git rev-parse --show-toplevel && cat VERSION && uname -s 2>/dev/null; echo "OS=$OS"; command -v python3 node git powershell pwsh 2>/dev/null
```
- Stop and tell the user if this is not the kit's repository (no `install.sh`,
  `install.ps1` and `VERSION` at the root).
- Platform: `OS=Windows_NT`, or `uname` printing MINGW/MSYS/CYGWIN → Windows.
  Linux, macOS (Darwin) and WSL → Unix.
- Unix needs `python3` or `node` (to merge settings safely). If both are
  missing, stop and say which one to install.

## 2. Install
- Unix: `bash install.sh $ARGUMENTS`
- Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File ./install.ps1`
  (add `-NoAutoUpdate` if `--no-auto-update` was given)

The installer merges into the user's existing `~/.claude/CLAUDE.md` and
`settings.json` (never overwrites them), backs up changed files, and is safe
to re-run. If it fails, show the last 20 lines of its output and stop.

## 3. Verify
Run `python3 scripts/verify_install.py` (on Windows try `python`, then `py`).
If no Python is available, check by hand instead: the files listed in
`~/.claude/enterprise-agents/manifest.txt` exist and contain no
`__CLAUDE_HOME__`; `~/.claude/CLAUDE.md` contains
`BEGIN claude-enterprise-agents`; `~/.claude/settings.json` has exactly one
`UserPromptSubmit` hook mentioning `prompt-reminder.txt` (and one
`SessionStart` hook mentioning `self-update` unless auto-update is off).

Do not report success unless verification passed. Show its real output.

## 4. Report (5 lines max)
- Installed version and target folder.
- Auto-update on/off. When on, the kit pulls new releases by itself in the
  background, at most once a day.
- **Restart Claude Code** (or reload the VS Code window) so the agents, `/build`
  and the rules load. Then `/agents` should list planner, researcher, coder,
  reviewer, cleaner.
- This cloned folder is no longer needed; updates come from the copy in
  `~/.claude/enterprise-agents/src`.
- Optional add-ons (graphify, Playwright CLI): see `INTEGRATION.md` §10. Do not
  install them unless the user asks.
