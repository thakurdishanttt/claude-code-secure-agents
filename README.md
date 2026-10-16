# claude-code-secure-agents

Enterprise multi-agent setup for [Claude Code](https://claude.com/claude-code): planner, researcher, coder, reviewer and cleaner subagents with a `/build` orchestrator that runs work in parallel, enforcing an OWASP LLM Top 10 + ASVS security standard on every prompt, across all projects.

---

## Why

Out of the box, Claude Code is one generalist working in a single context. This kit adds:

- **A team of specialist agents**, each with only the tools its role needs.
- **Security gates.** Nothing ships with a Critical or High finding.
- **Parallel execution.** Independent research, implementation steps and reviews run at the same time.
- **Global enforcement.** The rules apply to *every* project and are re-attached to *every* prompt automatically.

## What's included

| Component | Role | Tools |
|---|---|---|
| `planner` | Principal architect. Reads the code, builds a threat model, and splits the work into **parallel waves** with exclusive file ownership. | Read-only |
| `researcher` | Cited research from official sources, CVE and licence checks. Never puts code or secrets in search queries. | Web + Read |
| `coder` | Implements **one** plan step, touching only its assigned files, with tests and real verification output. | Edit + Bash |
| `reviewer` | Strict security and correctness gate. Returns **BLOCK / REQUEST CHANGES / APPROVE** with an attack scenario for every finding. | Read-only |
| `cleaner` | Behaviour-preserving cleanup that is forbidden from weakening any security control. | Edit |
| `/build` | The leader. Runs the gated pipeline below. | n/a |
| `ai-security.md` | A stack-agnostic security standard. See below. | n/a |
| `CLAUDE.md` + hook | Loads the rules at session start and re-injects them on every prompt. | n/a |

## The `/build` pipeline

```
/build add password reset with email tokens
```

```
Gate 0  Intake ─ ambiguous or insecure request? → ask first
Gate 1  Plan ── planner → threat model + waves ──→ ⏸ waits for your approval
Gate 2  Research ── researcher × N  (parallel)
Gate 3  Implement ── wave 1: coder × N (parallel, disjoint files)
                     wave 2: coder × N ...
Gate 4  Review ── reviewer[security] ‖ reviewer[correctness]  (parallel)
                  BLOCK → back to coder (max 3 cycles, then escalates to you)
Gate 5  Clean ── cleaner × N (parallel) → security re-check
Gate 6  Verify ── full test run, real output shown
```

## Security standard

[`standards/ai-security.md`](standards/ai-security.md) is binding on every agent. It is based on:

- **OWASP Top 10 for LLM Applications (2025):** prompt injection, sensitive data disclosure, supply chain, data poisoning, improper output handling, excessive agency, system prompt leakage, vector/embedding weaknesses, misinformation and unbounded consumption.
- **OWASP ASVS L2** and the **OWASP API Security Top 10:** authN/authZ, IDOR, injection, SSRF, path traversal, secrets, headers and containers.
- **NIST AI RMF** and **NIST SSDF**.

It works with any stack. Agents detect the project's stack (Python, Node/TS, Java/Kotlin, Go and others) and apply the matching tools. Projects can **add** stricter rules in their own `CLAUDE.md` or `.claude/standards/`, but can never relax the global ones.

## Quick start

```bash
git clone https://github.com/thakurdishanttt/claude-code-secure-agents.git
cd claude-code-secure-agents
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

**macOS / Linux / WSL:**
```bash
bash install.sh
```

Then **restart Claude Code** (or reload VS Code) and check the setup:

```
/agents   → planner, researcher, coder, reviewer, cleaner
/hooks    → UserPromptSubmit hook present
/memory   → ~/.claude/CLAUDE.md contains "Global working rules"
```

The installer:

- installs into your user config (`~/.claude`), so the setup applies to **all projects**
- **merges** into your existing `CLAUDE.md` and `settings.json` without overwriting them
- backs up every file it changes (`*.bak-<timestamp>`)
- can be run again safely to update

The full setup guide, covering manual hook setup, customising, uninstalling and troubleshooting, is in **[INTEGRATION.md](INTEGRATION.md)**.

## Repository layout

```
├── install.ps1              Windows installer
├── install.sh               macOS / Linux / WSL installer
├── INTEGRATION.md           Full setup & usage guide
├── CLAUDE.global.md         Global rules block → ~/.claude/CLAUDE.md
├── agents/                  planner · researcher · coder · reviewer · cleaner
├── commands/build.md        /build orchestrator
├── standards/ai-security.md Security standard
└── hooks/prompt-reminder.txt Text injected into every prompt
```

## Usage examples

```text
/build audit this codebase against the security standard and plan fixes
/build add rate limiting to all public API endpoints
Use the reviewer agent to audit my current changes
Use the researcher agent: does library X have known CVEs in version 2.x?
```

## Requirements

- Claude Code (CLI, VS Code / JetBrains extension, or desktop app)
- Windows: PowerShell 5.1 or later. macOS/Linux: `bash` plus `python3` or `node`.

## Notes and limitations

- **This guides Claude; it does not replace your controls.** It makes Claude plan, write and review code to an enterprise security standard. Keep SAST, dependency/CVE scanning, secret scanning and human review in your CI.
- **Built-in safety rules.** The agents never commit, push, deploy or delete data unless you explicitly ask.
- **Parallel agents cost more tokens.** They finish faster, but each run is capped at about 10 agents by default.
- **Managed environments may block hooks.** If your organisation enforces `allowManagedHooksOnly`, user hooks are ignored. The agents and `CLAUDE.md` still apply.

## Contributing

Issues and pull requests are welcome, especially stack mappings for more languages and new security checks.
