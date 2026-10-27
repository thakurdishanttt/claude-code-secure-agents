# Changelog

## v1.4.0 — 2026-10-27
- **Measured:** the same `/build` task (pagination + ownership check, 2 files, tests) cost $1.28 and 380 s of model time on v1.0, about $0.30 and 70–95 s on v1.3.0, and about $0.33–0.38 and 73–95 s on v1.4.0, with tests passing on every version. v1.4.0 costs slightly more than v1.3.0 because its reviewer can now actually read the security standard; on v1.3.0 that read was stuck behind a permission prompt.
- **Effort per agent:** `effort: high` for planner and reviewer, `medium` for coder and researcher, `low` for cleaner.
- **Parallelism where it pays:** `/build` uses parallel Explore scouts to locate code, runs the test suite while the reviewer works, and runs coders in parallel only on independent multi-file steps.
- **Per-call model/effort:** tier S reviews that touch no trust boundary run on Sonnet; mechanical coder steps run at `effort: low`.
- **No permission stalls:** installers add a read-only `Read(~/.claude/standards/**)` permission so agents read the standard without a prompt.
- **Shorter agent descriptions** (they load into every session).

## v1.3.0 — 2026-10-27
- **Faster, cheaper default:** global rules and the per-prompt reminder now say "work directly by default"; the full agent chain runs only through `/build`. The per-prompt reminder no longer pushes the agent team on every message.
- **Agent triggers:** the planner auto-runs only for tier L work (was: any change touching more than one file); the reviewer is no longer auto-spawned for questions and trivial one-line edits; the cleaner runs only when the reviewer flags dead code.
- **`/build` tier M:** the lead writes a short plan and implements itself (no fresh planner and coder re-reading the codebase), then one reviewer. It waits for approval only when the change adds a dependency or touches auth, secrets, crypto, model-callable tools or data deletion. Small review findings are fixed by the lead instead of a new coder.
- **Tighter caps:** `maxTurns` planner 25, reviewer 25, coder 40, researcher 15, cleaner 15; reviewer report capped at ~500 words.
- **Main session reads the standard via its index,** not the full file.

## v1.2.0 — 2026-10-22
- **Token efficiency:** `/build` now sizes work into tiers S/M/L (small changes: lead + 1 reviewer; default: planner → coder → 1 reviewer; full parallel pipeline only for large or boundary-crossing work). Every phase still has its gate.
- **Standard index** (`standards/ai-security-index.md`): agents read only the sections a change touches.
- **Context packs:** the lead gives each subagent its exact files, sections, research and callers.
- **Models and caps:** coder on Sonnet, cleaner on Haiku, planner and reviewer stay on Opus; `maxTurns` on every agent; output length caps.
- **Learnings:** new Gate 7 saves short project learnings to `.claude/learnings/` for the next run.
- **Optional add-ons:** graphify codebase map and Playwright CLI are used when installed; guidance for 21st.dev Magic MCP and Compound Engineering.
- **One-command setup:** open Claude Code in the cloned repo and run `/setup` (or say "set up this repo"); it installs globally, verifies with `scripts/verify_install.py`, and reports.
- **Upgrade on setup:** `/setup` fast-forwards a stale clone, then upgrades any older installed version (including v1.0) in place; installers refuse to downgrade a newer install (`--allow-downgrade` / `-AllowDowngrade` to override).
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
