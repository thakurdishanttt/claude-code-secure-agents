---
description: Install or upgrade this agent kit on this machine for every project (updates this checkout, runs the installer, verifies, reports)
argument-hint: "[--no-auto-update]"
---
Install the claude-code-secure-agents kit globally on this machine, so it
applies to every project and every prompt — or upgrade it if an older version
is already installed (any version, including v1.0 from before auto-update). Do it end to end without asking
questions unless a step fails. Keep output short.

Options from the user: $ARGUMENTS
(`--no-auto-update` disables the background self-update; default is on.)

## 1. Pre-checks (no shell commands needed)
- Use Glob to confirm `install.sh`, `install.ps1` and `VERSION` exist at the
  repository root; otherwise stop and say this is not the kit's repository.
- Platform: take it from your environment info. Windows (win32, or a
  MINGW/MSYS/Cygwin shell) → Windows installer. Linux, macOS and WSL → Unix
  installer. The installers check their own prerequisites and say what is
  missing.

## 1b. Bring this checkout up to date (so an old clone installs the latest)
Run `git fetch --quiet origin`, then `git status -sb`.
- If the fetch fails (offline, no access): continue with this checkout and say so.
- If the branch is the default branch (`main`), the working tree is clean and
  the status shows `[behind N]`: run `git pull --ff-only`.
- If it is on another branch, has local changes, or has diverged: do not
  touch it. Install it as is and tell the user it may not be the latest.

## 2. Install
- Unix: `bash install.sh $ARGUMENTS`
- Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File ./install.ps1`
  (add `-NoAutoUpdate` if `--no-auto-update` was given)

The installer merges into the user's existing `~/.claude/CLAUDE.md` and
`settings.json` (never overwrites them), backs up changed files, and is safe
to re-run. It upgrades an older installed kit in place and prints
"Upgrading X -> Y" (or "Reinstalling … already up to date" for the same version). If the machine already has a *newer* version than this
checkout, it changes nothing and says so — report that as "already up to
date" (do not pass `--allow-downgrade` unless the user explicitly asks). If it fails, show the last 20 lines of its output and stop.

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
- Installed version and target folder; for an upgrade, "upgraded from X to Y"
  (or "already up to date").
- Auto-update on/off. When on, the kit pulls new releases by itself in the
  background, at most once a day.
- **Restart Claude Code** (or reload the VS Code window) so the agents, `/build`
  and the rules load. Then `/agents` should list planner, researcher, coder,
  reviewer, cleaner.
- This cloned folder is no longer needed; updates come from the copy in
  `~/.claude/enterprise-agents/src`.
- Optional add-ons (graphify, Playwright CLI): see `INTEGRATION.md` §10. Do not
  install them unless the user asks.
