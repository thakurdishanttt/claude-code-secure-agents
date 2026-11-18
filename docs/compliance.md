# Compliance mapping

How the controls in this kit and in [claude-secure-agents-skills](https://github.com/thakurdishanttt/claude-secure-agents-skills) support common audit frameworks, and what evidence they leave behind.

> **Read this first.** These tools help your teams *perform* and *evidence* secure-development activities. They do not, on their own, make an organization compliant with any framework, and they are not certified by any standards body. Your auditor decides whether a control is met, based on your whole process. Control names below are paraphrased; the official texts are the AICPA Trust Services Criteria, ISO/IEC 27001:2022 Annex A, PCI DSS v4.0 and NIST SP 800-218.

## Capabilities

| # | Capability | In the kit | In the skills |
|---|---|---|---|
| C1 | Written secure-coding standard (OWASP LLM Top 10 2025, Agentic Top 10 2026, ASVS L2), binding on every change | `standards/ai-security.md`, global `CLAUDE.md` block, per-prompt hook | `ai-security-standard`; every skill ships the standard |
| C2 | Organization-specific security requirements, enforced by rule ID | project `CLAUDE.md`, `.claude/standards/*.md` | `.security/rules.md` |
| C3 | Threat modelling before implementation | `planner` (threat model per trust boundary), `/build` Gate 1 | `threat-model`, `secure-feature-build` |
| C4 | Independent security and correctness review before merge, with a blocking verdict | `reviewer`, `/build` Gate 4 | `secure-code-review`, `iac-security-review` |
| C5 | Machine-readable findings for code scanning | — | SARIF 2.1.0 ([ci-integration](https://github.com/thakurdishanttt/claude-secure-agents-skills/blob/main/docs/ci-integration.md)) |
| C6 | Tests with real output, including negative and abuse cases | `coder`, `/build` Gates 3 and 6 | `secure-feature-build` |
| C7 | Third-party component vetting (CVEs, maintenance, licence, typosquatting) | `researcher` | `dependency-vetting` |
| C8 | Infrastructure and pipeline configuration review | — | `iac-security-review` |
| C9 | Controlled change of the tooling itself: PR review, CODEOWNERS, guardrail CI that blocks weakened rules, versioned releases. Automated updates pass the same guardrails plus an independent reviewer before release | `scripts/validate.py`, `validate.yml`, `auto-update.yml`, `CHANGELOG.md`, GitHub Releases | `validate_skills.py`, `release.yml` with `SHA256SUMS` |
| C10 | Measured quality of the tooling | `evals/` (hidden acceptance tests) | `evals/` (skill selection, detection, false positives) |

## Framework mapping

| Framework control | Supported by | Evidence you can show |
|---|---|---|
| **SOC 2** CC3.2: risk identification and analysis | C3 | Threat models in plans or design docs |
| **SOC 2** CC6.1: logical access security | C1, C4 | Review findings on authN/authZ, secrets and tenant isolation |
| **SOC 2** CC7.1: configuration and vulnerability detection | C7, C8, C5 | Vetting verdicts, IaC review reports, code-scanning alerts |
| **SOC 2** CC8.1: authorized, tested and approved changes | C4, C6, C9 | PRs with review verdicts and test output; the kit's own PR and release history |
| **SOC 2** CC9.2: vendor and business-partner risk | C7 | Vetting verdicts for model APIs, SDKs and MCP servers |
| **ISO/IEC 27001:2022** A.5.21: ICT supply-chain security | C7 | Dependency vetting records |
| **ISO/IEC 27001:2022** A.8.8: technical vulnerability management | C7, C5 | CVE findings and remediation in PRs |
| **ISO/IEC 27001:2022** A.8.9: configuration management | C8 | IaC review reports |
| **ISO/IEC 27001:2022** A.8.25: secure development life cycle | C1, C3, C4, C6 | `/build` or `secure-feature-build` runs: plan → review → tests |
| **ISO/IEC 27001:2022** A.8.26: application security requirements | C1, C2 | The standard and `.security/rules.md` under version control |
| **ISO/IEC 27001:2022** A.8.27: secure architecture and engineering principles | C3 | Threat models |
| **ISO/IEC 27001:2022** A.8.28: secure coding | C1, C4 | Standard plus review verdicts per change |
| **ISO/IEC 27001:2022** A.8.29: security testing in development and acceptance | C6, C4 | Test output and negative tests in PRs |
| **ISO/IEC 27001:2022** A.8.32: change management | C9 | PR history, CODEOWNERS approvals, releases |
| **PCI DSS v4.0** 6.2.1: bespoke and custom software developed securely | C1, C3 | Standard, threat models |
| **PCI DSS v4.0** 6.2.3: code reviewed before release | C4, C5 | Review verdict or SARIF results on every PR |
| **PCI DSS v4.0** 6.2.4: techniques to prevent common attacks (injection and others) | C1, C4 | Standard sections §5 and §11; findings |
| **PCI DSS v4.0** 6.3.1: vulnerabilities identified and managed | C7 | Vetting verdicts with CVE references |
| **PCI DSS v4.0** 6.5.1: production changes follow procedures | C9 | PR and release records |
| **NIST SSDF** PO.1: define security requirements | C1, C2 | Standard and org rules |
| **NIST SSDF** PW.1: design to meet requirements and mitigate risk | C3 | Threat models |
| **NIST SSDF** PW.4: reuse well-secured software | C7 | Vetting verdicts |
| **NIST SSDF** PW.5: secure coding practices | C1 | Standard applied per change |
| **NIST SSDF** PW.7: review code for vulnerabilities | C4, C5 | Review verdicts, SARIF |
| **NIST SSDF** PW.8: test executable code | C6 | Test output |
| **NIST SSDF** PW.9: secure default configuration | C8 | IaC findings and fixes |
| **NIST SSDF** RV.1: identify and confirm vulnerabilities | C7, C4 | Findings with CVE or attack scenario |
| **NIST SSDF** PS.1 and PS.3: protect code and archive releases | C9 | Branch protection (you configure), tagged releases with checksums |

## What these tools do not cover
- **Developer security training** (PCI DSS 6.2.2): not provided.
- **Software inventory or SBOM** (PCI DSS 6.3.2): not generated. Use a dedicated SBOM tool.
- **Patch deployment** (PCI DSS 6.3.3) and production monitoring (SOC 2 CC7.2): out of scope.
- **SAST, DAST, penetration testing:** these tools complement them, but don't replace them. Keep your scanners and human review for high-risk releases.
- **Branch protection and approvals:** the evidence for CC8.1 and A.8.32 depends on you protecting `main` and requiring reviews in GitHub.

## Keeping evidence
- Keep PRs as the record: put the review verdict (or SARIF upload) and test output on each PR.
- Keep threat models with the design docs or in the PR description.
- Version `.security/rules.md` in each repository.
- Pin tool versions with release tags, so you can show which version of the standard applied at a given time.
