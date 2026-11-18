# Contributing

The files in this repo are installed into every developer's `~/.claude`, so
every change is a release to every developer who uses the kit.

## Ground rules
- Security rules may be **added or tightened, never relaxed**.
- `planner`, `researcher` and `reviewer` stay read-only. No agent gets `bypassPermissions`.
- Installers, hooks, `scripts/` and `.github/` are human-only; the auto-update run may change only kit content.
- Keep `__CLAUDE_HOME__` placeholders in kit files; the installers substitute real paths.
- Verify Claude Code behaviour against the [official docs](https://code.claude.com/docs) before relying on it.

## Making a change
1. Branch from `main`.
2. Make the change.
3. Run the gates:
   ```bash
   python3 scripts/validate.py --base origin/main   # must pass
   python3 scripts/run_evals.py                     # required for agents/, commands/, standards/ (~$2)
   bash install.sh && python3 scripts/verify_install.py   # installer still works
   ```
4. For anything users will notice, bump `VERSION` (semver) and add a `CHANGELOG.md` entry.
5. Open a PR with the template and paste the eval table. A CODEOWNERS review is required. When `VERSION` changes, CI publishes the release after merge.

## What the guardrails block
`scripts/validate.py --base` fails a PR that:
- removes, weakens or narrows a MUST / NEVER / Forbidden / Do NOT rule;
- adds exception wording such as "unless" or "optional" to a rule file;
- gives an agent more tools, or adds permission-bearing frontmatter;
- adds secrets, symlinks, hard-coded user paths or pipe-to-shell commands.

In `--bot` mode (used by the auto-update pipeline) it also rejects any change outside kit content paths.

If a change like that is truly intended, change the validator in the same PR so the reviewer sees it explicitly.

## Reporting bugs
- A wrong or unsafe agent behaviour: open an issue with the prompt and a minimal repo.
- A security vulnerability: follow [SECURITY.md](SECURITY.md) instead.
