# Claude Code Enterprise Agent Team: Setup Guide

This package installs, for **every project on your machine**:

- **Five specialist subagents.** `planner`, `researcher`, `coder`, `reviewer` and `cleaner`.
- **A leader command, `/build`.** It runs those agents as a gated pipeline (plan → research → build → review → clean → test), running independent work in parallel.
- **An enterprise AI and application security standard.** It is based on the OWASP Top 10 for LLM Applications 2025, OWASP ASVS L2, OWASP API Top 10, NIST AI RMF and NIST SSDF, and every agent must follow it.
- **Automatic enforcement on every prompt:**
  - a global `CLAUDE.md`, loaded at the start of every session
  - a `UserPromptSubmit` hook, which re-attaches the core rules to every prompt you send

Install time: about 2 minutes.

---

## 1. Requirements

- **Claude Code**, used as the CLI, the VS Code / JetBrains extension, or the desktop app.
- **Windows:** PowerShell 5.1 or later (built in).
- **macOS / Linux / WSL:** `bash`, plus `python3` or `node`. These are used to merge settings safely.
- **git** on the machine, for automatic updates (optional; without it the kit works but does not self-update).

## 2. What's in the zip

```
claude-enterprise-agents/
├── install.ps1              # Windows installer
├── install.sh               # macOS / Linux / WSL installer
├── INTEGRATION.md           # this guide
├── CLAUDE.global.md         # global rules block (goes into ~/.claude/CLAUDE.md)
├── agents/
│   ├── planner.md           # Principal architect: threat model + parallel waves
│   ├── researcher.md        # Cited research, CVE/licence checks, no data leakage
│   ├── coder.md             # Implements one step, exclusive files, tests required
│   ├── reviewer.md          # Read-only security/correctness gate: BLOCK / APPROVE
│   └── cleaner.md           # Behaviour-preserving cleanup, never weakens security
├── commands/
│   └── build.md             # /build: the leader / orchestrator
├── standards/
│   └── ai-security.md       # The security standard (stack-agnostic)
└── hooks/
    └── prompt-reminder.txt  # Text injected into every prompt
```

## 3. Install

**Easiest:** open Claude Code in the cloned or unzipped folder (`claude`) and type `/setup`, or say *"set up this repo"*. Claude runs the right installer for your OS, verifies the result with `scripts/verify_install.py`, and tells you to restart. The repo ships `.claude/settings.json` pre-approving only the installer and verifier commands, so setup runs without permission prompts once you trust the folder.

**Manually:** open a terminal **in the folder** and run the command for your system.

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

**macOS / Linux / WSL:**
```bash
bash install.sh
```

The installer:

1. **Copies the files.** Agents, the command, the standard and the hook text go into your user config folder (`%USERPROFILE%\.claude` on Windows, `~/.claude` elsewhere). Paths are filled in for your machine automatically.
2. **Adds the rules to your global `CLAUDE.md`.** Your existing content is kept, and the rules go in a marked block.
3. **Adds the hook to `settings.json`.** Your existing permissions and settings are kept.
4. **Backs up every file it changes**, as `<file>.bak-<timestamp>`.

5. **Enables automatic updates.** Adds a background `SessionStart` hook and keeps a release checkout in `~/.claude/enterprise-agents/src`. Opt out with `--no-auto-update` (`-NoAutoUpdate` on Windows).

It is safe to run again. A second run changes only what differs, replaces the rules block, never adds duplicate hooks, and keeps at most 5 backups per file.

**Then restart Claude Code**, or reload the VS Code window.

## 4. Verify

| Check | How | Expected |
|---|---|---|
| Agents loaded | Run `/agents` | planner, researcher, coder, reviewer, cleaner listed under *User* |
| Hook active | Run `/hooks` | A `UserPromptSubmit` hook running `cat ".../hooks/prompt-reminder.txt"` and a `SessionStart` hook running `self-update` |
| Version | `cat ~/.claude/enterprise-agents/VERSION` | Matches the latest release |
| Rules loaded | Run `/memory` | User memory `~/.claude/CLAUDE.md` contains *Global working rules* |
| End-to-end | Ask: *"What standing rules apply to this prompt?"* | Claude quotes the security, multi-agent and safety rules |

### Manual hook setup (only if the installer warned you)

Add this to `~/.claude/settings.json`, merging with what is already there. Replace the path with your own absolute path.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "cat \"/ABSOLUTE/PATH/TO/.claude/hooks/prompt-reminder.txt\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

## 5. Daily use

**Full pipeline for a feature:**
```
/build add password reset with email tokens
```
`/build` then works through its steps in order:

1. **Plan.** It asks the planner for a plan and waits for your approval.
2. **Research.** It researches open questions in parallel.
3. **Build.** It implements in parallel waves, never with two coders on the same file.
4. **Review.** A security reviewer and a correctness reviewer run in parallel. Any **Critical** or **High** finding blocks the work, and it loops back to the coder up to 3 times before escalating to you.
5. **Clean.** It cleans up, then re-checks that no security control was weakened.
6. **Test.** It runs the tests and reports the real output.

**Single agent:**
```
Use the reviewer agent to audit my current changes
Use the researcher agent: is library X affected by any CVEs?
```

**Without `/build`:** the global rules still apply on every prompt. Claude will use agents in parallel for non-trivial work and work directly on trivial tasks.

**Recommended first run on an existing project:**
```
/build audit this codebase against the security standard and plan fixes
```

## 6. Customising

- **Add project-specific rules** in that project's `CLAUDE.md` or `.claude/standards/*.md`. They can **add or tighten** rules but never relax the global standard.
- **Change models or tools** for an agent by editing the frontmatter in `~/.claude/agents/<name>.md`. Model options are `opus`, `sonnet`, `haiku` or `inherit`.
- **Change the per-prompt reminder** by editing `~/.claude/hooks/prompt-reminder.txt`. Keep it short, because it is added to every prompt.
- **Avoid project agents with the same names.** A project's `.claude/agents/` overrides user agents with the same name, so delete any duplicates in a project if you want the global versions.

## 7. Uninstall

1. Delete every file listed in `~/.claude/enterprise-agents/manifest.txt`, then the `~/.claude/enterprise-agents/` folder.
2. In `~/.claude/CLAUDE.md`, remove everything between `<!-- BEGIN claude-enterprise-agents -->` and `<!-- END claude-enterprise-agents -->`.
3. Remove the `prompt-reminder` and `self-update` hooks with `/hooks`, or delete their entries in `~/.claude/settings.json`. You can also restore a `settings.json.bak-*` backup.

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Agents not listed | Restart Claude Code. Check the files are in `~/.claude/agents/`, not in a project folder. |
| Hook not running | Run `/hooks` once to reload, or restart. Check `settings.json` is valid JSON, because one syntax error disables the whole file. |
| `cat` not found (Windows) | Claude Code runs hooks in Git Bash or PowerShell, and both support `cat`. If you use another shell, change the command to `type "C:\path\to\prompt-reminder.txt"`. |
| Hooks ignored on a company laptop | Your organisation may enforce managed settings (`allowManagedHooksOnly`). Ask IT to deploy the hook through managed settings. `CLAUDE.md` and the agents still work. |
| PowerShell blocks the script | Use the `-ExecutionPolicy Bypass` form shown above. It only applies to that one run. |

## 9. Important notes

- **This guides Claude; it does not replace your controls.** The standard makes Claude plan, write and review code to enterprise security requirements. Keep your normal CI security scanning (SAST, dependency/CVE scanning, secret scanning) and human code review.
- **Built-in safety rules.** The agents never commit, push, deploy or delete data unless you explicitly ask.
- **Token usage.** Parallel agents finish faster but use more tokens than a single session. Each run is capped at about 10 agents unless you ask for more.

## 10. Optional add-ons (token savers)

None of these are installed by the kit; enable them per machine or project after your security review.

| Add-on | Use it for | Install | Enterprise notes |
|---|---|---|---|
| [graphify](https://github.com/Graphify-Labs/graphify) | Codebase knowledge graph; agents query it instead of grepping. Gains grow with repo size (tiny repos: ~none). | `pipx install graphifyy && graphify install`, then `/graphify .` in the project | Code is parsed locally (tree-sitter). Docs, PDFs and images are sent to a model for extraction — exclude them for confidential repos. Add `graphify-out/` to `.gitignore` unless you want it shared. The PyPI name is `graphifyy`; verify it against the GitHub repo. |
| [Playwright CLI](https://playwright.dev) | Browser verification of UI changes, ~4× fewer tokens than the Playwright MCP server because snapshots go to files. | Follow the Playwright docs for `@playwright/cli` and its Claude Code skill | Prefer it over the Playwright MCP server in this kit. |
| [21st.dev Magic MCP](https://21st.dev) | Generating React/Tailwind UI components. | Per project, not globally | Sends your prompts to a third-party service and needs an API key; only for frontend projects your data policy allows. |
| [Compound Engineering plugin](https://github.com/EveryInc/compound-engineering-plugin) | Its idea — saving learnings after each task — is built into `/build` (Gate 7). | Not recommended alongside this kit | Its `/lfg` commits and opens PRs on its own, which conflicts with this kit's never-commit rule, and its review spawns its own agents on top of ours. |

## 11. Automatic updates

### How it works
1. **Upstream watch** (`.github/workflows/auto-update.yml`, daily 01:17 UTC, also runnable by hand). `scripts/check_upstream.py` checks the sources in `.github/automation/sources.json`: the Claude Code changelog and docs (subagents, hooks, settings, slash commands, skills, memory, security, permissions), GitHub advisories for Claude Code, claude-code-action releases, OWASP LLM and Agentic Top 10, MITRE ATLAS and NIST AI RMF. Cosmetic page churn is filtered out. The first run is a full baseline audit.
2. **Update** (job `propose`, read-only GitHub token, no git credentials). Claude (via `anthropics/claude-code-action`) reads the change report and edits kit content only — `agents/`, `commands/`, `standards/`, `hooks/prompt-reminder.txt`, `CLAUDE.global.md` and the docs. Its write tools are path-scoped, it can fetch only official domains, and it cannot commit, push, delete or run anything except the validator. Installers and hook scripts are human-only; if one needs a change, the run opens an issue instead.
3. **Gates.** The validator runs from a read-only copy pinned from `main` outside the workspace, and every guardrail, `.git/config` and the watcher state are hash-checked after each Claude step. The validator fails the release if any security or safety rule is removed, weakened, narrowed or given an exception; if any agent gains tools, MCP servers, hooks or permissions; if `bypassPermissions`, a pipe-to-shell download, a secret, a symlink or a hard-coded path appears; or if files outside kit content change. One automatic fix cycle runs on failure. Then a separate job (`review`) applies the patch to a fresh checkout and an independent Claude reviewer with **no write tools** returns APPROVE / REQUEST_CHANGES / BLOCK — that verdict is the release gate.
4. **Ship** (job `ship`, the only job with write access). A fresh checkout of `main` accepts the patch only if every path is kit content, re-runs `main`'s validator, bumps VERSION (minor for new agents/commands, patch otherwise), opens a PR and, if the gate approved, merges it and publishes release `vX.Y.Z`.
5. **Fleet update.** On each machine the `SessionStart` hook runs in the background at most once a day and picks the newest release tag that is on `main`, carries a matching `VERSION`, was never moved upstream, and (if required) is signed. It never downgrades, then re-runs the installer. Changes apply from the next session. Log: `~/.claude/enterprise-agents/update.log`.

If a gate fails, nothing ships: the PR is labelled `needs-human-review` and an issue is opened. A pipeline error also opens an issue; the next run retries.

### One-time setup (repo admin)
| Setting | Where | Value |
|---|---|---|
| `ANTHROPIC_API_KEY` **or** `CLAUDE_CODE_OAUTH_TOKEN` | Settings → Secrets → Actions | Required. Use a dedicated key with a spend limit. |
| Workflow permissions | Settings → Actions → General | "Read and write" + "Allow GitHub Actions to create and approve pull requests" |
| `AUTOMATION_TOKEN` (optional) | Secrets | GitHub App or fine-grained PAT, only if branch protection blocks the default token from merging |
| `CLAUDE_MODEL` (optional) | Variables | Model alias or ID, default `opus` |
| `AUTO_MERGE` (optional) | Variables | `false` = open PRs but let a human merge |
| `AUTO_UPDATE_ENABLED` (optional) | Variables | `false` = kill switch for the whole loop |

### Controls on developer machines
| Need | How |
|---|---|
| Turn off auto-update | Re-run the installer with `--no-auto-update`, or set `CLAUDE_AGENTS_AUTO_UPDATE=0` |
| Check less often | `CLAUDE_AGENTS_UPDATE_INTERVAL_HOURS=72` |
| Only install signed releases | `CLAUDE_AGENTS_REQUIRE_SIGNED_TAGS=1` (sign tags in your release process) |
| Pull from an internal mirror | Install with `CLAUDE_AGENTS_REPO=https://git.internal/…/claude-code-secure-agents.git` |

### Adding a watched source
Add an entry to `.github/automation/sources.json` (kinds: `changelog`, `page`, `gh_release`, `gh_advisories`) and its host to `allowed_hosts`. Only humans can change this file.

