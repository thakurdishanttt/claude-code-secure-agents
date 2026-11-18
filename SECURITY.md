# Security policy

## Reporting a vulnerability
Please **do not open a public issue**. Report privately through GitHub's
[private vulnerability reporting](https://github.com/thakurdishanttt/claude-code-secure-agents/security/advisories/new)
(Security tab → "Report a vulnerability"), or email thakurdishant1853@gmail.com.

Include the kit version (`~/.claude/enterprise-agents/VERSION`), the Claude Code
version, your OS, and steps or a prompt that reproduces the issue.

| Stage | Target |
|---|---|
| Acknowledgement | 3 business days |
| Triage and severity | 7 business days |
| Fix for Critical / High | 30 days, released as a new version |

## In scope
- The installers (`install.sh`, `install.ps1`) and the self-updater (`hooks/self-update.sh`, `hooks/self-update.ps1`): anything that could damage a user's settings, run untrusted code, write outside `~/.claude`, or install a release that did not come from `main`.
- The auto-update pipeline (`.github/workflows/auto-update.yml` and `scripts/`): any way for upstream content or the update run to ship a weakened rule, touch the guardrails, or reach a write token.
- Agents, `/build` or the global rules leading Claude to leak data, follow injected instructions, act outside its permissions, or commit, push, deploy or delete data without being asked.
- A rule in `standards/ai-security.md` that is wrong or unsafe.
- Weaknesses in the guardrails (`scripts/validate.py`) that would let a weakened rule or widened permission through CI.

## Security model
- **Hooks.** `UserPromptSubmit` re-attaches the rules text to prompts. A background `SessionStart` hook checks for a new release at most once a day.
- **Self-update.** It installs only release tags that are on `main`, carry a matching `VERSION`, were never moved upstream, and (with `CLAUDE_AGENTS_REQUIRE_SIGNED_TAGS=1`) are signed. It never downgrades. Opt out with `CLAUDE_AGENTS_AUTO_UPDATE=0` or `install.sh --no-auto-update`; point it at an internal mirror with `CLAUDE_AGENTS_REPO`.
- **Auto-update pipeline.** Claude edits only kit content, in a job with a read-only token. Guardrails are pinned from `main` and hash-checked. An independent reviewer with no write tools gates the release. Installers, hooks, `scripts/` and `.github/` are human-only.
- **Least privilege.** `planner`, `researcher` and `reviewer` are read-only (`disallowedTools: Edit, Write, NotebookEdit`). No agent uses `bypassPermissions`. The installer adds one permission: read-only access to `~/.claude/standards/`.
- **Untrusted content is data.** Rules and agents treat repository, web and tool content as data, never instructions.
- **Change control.** Every change, human or automated, goes through a pull request. CI blocks removed or weakened rules, exceptions added to rules, widened agent permissions, secrets, symlinks, background hooks and pipe-to-shell commands.
- **Backups.** The installer backs up every file it changes (at most 5 backups per file) and never deletes your own content.

## Supported versions
Only the latest release is supported. Machines with auto-update on pick it up within a day; otherwise upgrade with `git pull` and `/setup` (or the installer).
