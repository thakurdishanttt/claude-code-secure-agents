# Changelog

## v1.2.0 — 2026-10-22
- **Token efficiency:** `/build` now sizes work into tiers S/M/L (small changes: lead + 1 reviewer; default: planner → coder → 1 reviewer; full parallel pipeline only for large or boundary-crossing work). Every phase still has its gate.
- **Standard index** (`standards/ai-security-index.md`): agents read only the sections a change touches.
- **Context packs:** the lead gives each subagent its exact files, sections, research and callers.
- **Models and caps:** coder on Sonnet, cleaner on Haiku, planner and reviewer stay on Opus; `maxTurns` on every agent; output length caps.
- **Learnings:** new Gate 7 saves short project learnings to `.claude/learnings/` for the next run.
- **Optional add-ons:** graphify codebase map and Playwright CLI are used when installed; guidance for 21st.dev Magic MCP and Compound Engineering.
- **One-command setup:** open Claude Code in the cloned repo and run `/setup` (or say "set up this repo"); it installs globally, verifies with `scripts/verify_install.py`, and reports.
- **Pipeline cost:** Claude runs only on kit-relevant changelog entries, advisories and releases; docs-page changes are batched weekly; updates on Sonnet with lower turn caps, release gate on Opus.

## v1.1.0 — 2026-10-16
- **Zero-touch maintenance:** daily GitHub Actions pipeline detects Claude Code feature changes and AI-security updates, has Claude update the kit, gates it (no-weakening validator + independent reviewer + one fix cycle), and auto-releases.
- **Fleet self-update:** background `SessionStart` hook installs new releases on developer machines (main-only tags, no downgrades, optional signed tags, opt-out, internal mirror support).
- **Standard:** added §14 OWASP Top 10 for Agentic Applications (2026) and §15 rules for the coding agents themselves; MITRE ATLAS added to baselines.
- **Agents:** planner, researcher and reviewer now declare `disallowedTools: Edit, Write, NotebookEdit`; reviewer and planner cover ASI01–ASI10.
- **Installers:** install every file in `agents/`, `commands/`, `standards/` automatically, stage before writing, back up only changed files (max 5), retire files dropped by a release, write a manifest.
- **CI:** `validate.yml` runs guardrails plus Linux and Windows install smoke tests on every PR.

## v1.0.0
- Initial kit: planner, researcher, coder, reviewer, cleaner, `/build`, security standard, global rules and prompt hook.
