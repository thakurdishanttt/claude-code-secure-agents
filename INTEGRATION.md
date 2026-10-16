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

Unzip anywhere, open a terminal **in the unzipped folder**, and run the command for your system.

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

It is safe to run again, for example to update. A second run replaces the rules block and does not add a duplicate hook.

**Then restart Claude Code**, or reload the VS Code window.

## 4. Verify

| Check | How | Expected |
|---|---|---|
| Agents loaded | Run `/agents` | planner, researcher, coder, reviewer, cleaner listed under *User* |
| Hook active | Run `/hooks` | A `UserPromptSubmit` hook running `cat ".../hooks/prompt-reminder.txt"` |
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

1. Delete these from `~/.claude/`:
   - `agents/planner.md`, `agents/researcher.md`, `agents/coder.md`, `agents/reviewer.md`, `agents/cleaner.md`
   - `commands/build.md`
   - `standards/ai-security.md`
   - `hooks/prompt-reminder.txt`
2. In `~/.claude/CLAUDE.md`, remove everything between `<!-- BEGIN claude-enterprise-agents -->` and `<!-- END claude-enterprise-agents -->`.
3. Remove the hook with `/hooks`, or delete its entry in `~/.claude/settings.json`. You can also restore the `settings.json.bak-*` backup.

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
