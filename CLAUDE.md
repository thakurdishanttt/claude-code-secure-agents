# claude-code-secure-agents

## If the user asks to set up, install or configure this kit
("set up this repo", "install this", "setup", …): run the `/setup` procedure in
`.claude/commands/setup.md` end to end — install, verify, report. That is all
they want; do not edit or review the repository.

# Maintaining this repository

This repo **is** the claude-code-secure-agents kit. The files under `agents/`,
`commands/`, `standards/`, `hooks/` and `CLAUDE.global.md` are installed into
every developer's `~/.claude`, and installed machines auto-update to each new
release. Treat every change as a production deploy to the whole fleet.

## Layout
| Path | What it is | Who edits it |
|---|---|---|
| `agents/`, `commands/`, `standards/`, `hooks/prompt-reminder.txt`, `CLAUDE.global.md` | The kit | Humans and the auto-update run |
| `install.sh`, `install.ps1`, `hooks/self-update.*` | Installers and the self-updater (run on every machine) | **Humans only** |
| `README.md`, `INTEGRATION.md`, `CHANGELOG.md` | Docs | Humans and the auto-update run |
| `scripts/`, `.github/workflows/`, `.github/automation/`, `.claude/` | The update pipeline, its guardrails, and the `/setup` command | **Humans only** |
| `VERSION` | Release version, stamped by the pipeline | Pipeline only |

## Rules for any change
- Security rules may be added or tightened, never removed or relaxed.
  `scripts/validate.py` fails the build if a normative line (MUST / NEVER /
  Forbidden / Do NOT) disappears without an equivalent replacement.
- planner, researcher and reviewer stay read-only. No agent gets
  `bypassPermissions`.
- Keep `__CLAUDE_HOME__` placeholders; the installers substitute real paths.
- Verify Claude Code behaviour against the official docs
  (https://code.claude.com/docs) before relying on it.
- Run `python3 scripts/validate.py` before finishing.
