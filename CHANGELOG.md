# Changelog

## v1.1.0 — 2026-10-16
- **Zero-touch maintenance:** daily GitHub Actions pipeline detects Claude Code feature changes and AI-security updates, has Claude update the kit, gates it (no-weakening validator + independent reviewer + one fix cycle), and auto-releases.
- **Fleet self-update:** background `SessionStart` hook installs new releases on developer machines (main-only tags, no downgrades, optional signed tags, opt-out, internal mirror support).
- **Standard:** added §14 OWASP Top 10 for Agentic Applications (2026) and §15 rules for the coding agents themselves; MITRE ATLAS added to baselines.
- **Agents:** planner, researcher and reviewer now declare `disallowedTools: Edit, Write, NotebookEdit`; reviewer and planner cover ASI01–ASI10.
- **Installers:** install every file in `agents/`, `commands/`, `standards/` automatically, stage before writing, back up only changed files (max 5), retire files dropped by a release, write a manifest.
- **CI:** `validate.yml` runs guardrails plus Linux and Windows install smoke tests on every PR.

## v1.0.0
- Initial kit: planner, researcher, coder, reviewer, cleaner, `/build`, security standard, global rules and prompt hook.
