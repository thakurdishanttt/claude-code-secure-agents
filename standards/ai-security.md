# Enterprise AI & Application Security Standard

Global standard for every project and every agent. A change that violates a
**MUST** rule is not shippable, regardless of deadline.

Baselines: OWASP Top 10 for LLM Applications (2025), OWASP ASVS L2,
OWASP API Security Top 10, NIST AI RMF, NIST SSDF.

## 0. How to apply this standard
- It is stack-agnostic. Before applying it, detect the project's stack
  (language, framework, datastores, LLM/vector providers, deploy target) from
  manifests (`requirements.txt`, `pyproject.toml`, `package.json`, `go.mod`,
  `pom.xml`, `Dockerfile`, IaC) and map each rule to that stack's idiom
  (see §13).
- Project-specific rules may ADD to this standard. They live in the project's
  `CLAUDE.md` or `.claude/standards/*.md`. They may never relax a MUST rule.
- Sections 1–10 apply to any project that calls an LLM, embeds content, or
  exposes tools to a model. Sections 11–12 apply to every project.

---

## 1. Prompt injection (LLM01)
- MUST treat user messages, retrieved documents, uploaded files, filenames,
  web pages, tool results, and emails as untrusted data, never instructions.
- MUST keep system instructions separate from untrusted content. Never
  concatenate untrusted text into the system prompt.
- MUST delimit untrusted context and instruct the model that it is reference
  material only.
- MUST NOT let model output trigger privileged actions (writes, deletes,
  payments, outbound requests, tool calls with side effects) without
  server-side validation and authorization of that specific action.

## 2. Sensitive information disclosure (LLM02)
- MUST NOT log full prompts, completions, document text, credentials, tokens,
  or PII. Log IDs, counts, latencies, and hashes.
- MUST NOT expose system prompts, internal config, stack traces, or other
  users' data in responses or model output.
- MUST enforce per-user/per-tenant authorization at data-access time
  (DB query, vector-store filter, object-store ACL), not only in the UI.
- Data sent to third-party model providers MUST be minimized and permitted by
  the project's data-handling policy.

## 3. Supply chain (LLM03)
- New dependencies MUST be pinned (exact or bounded range), from official
  registries, maintained, license-compatible, and free of known critical CVEs.
  Justify every new dependency.
- Model names/IDs and endpoints MUST come from configuration.
- Third-party models, datasets, and plugins MUST come from trusted sources.

## 4. Data & model poisoning (LLM04)
- Ingested/uploaded content MUST be validated: allowed type (extension AND
  magic bytes), size limit, structural limits, rejection of malformed or
  encrypted files.
- Ingested content MUST carry provenance (uploader, time, source, ID) so it
  can be audited and purged.

## 5. Improper output handling (LLM05)
- Model output is untrusted. Escape/encode for the sink: HTML (no
  `innerHTML`/`dangerouslySetInnerHTML` with model text), SQL (parameterize),
  shell (never), file paths (never), URLs (allow-list), `eval` (never).
- Spreadsheet/CSV exports MUST neutralize formula injection
  (cells starting with `= + - @ \t \r`).
- Structured output MUST be schema-validated before use.

## 6. Excessive agency (LLM06)
- Model-callable tools MUST be least-privilege, allow-listed, have validated
  arguments, bounded results, and require human confirmation for
  irreversible or high-impact actions.
- No tool may run arbitrary code, reach arbitrary URLs, or access files
  outside an allow-listed directory.

## 7. System prompt leakage (LLM07)
- System prompts MUST NOT contain secrets, credentials, internal URLs, or
  authorization logic. Authorization is enforced in code.

## 8. Vector & embedding weaknesses (LLM08)
- Vector stores MUST require authentication and not be publicly reachable.
- Every similarity query MUST apply the caller's access filter.
- Deleting a source MUST delete its embeddings.

## 9. Misinformation (LLM09)
- Answers presented as factual MUST be grounded in sources and cite them.
  When context is insufficient, the system says so.

## 10. Unbounded consumption (LLM10)
- Every LLM, embedding, and outbound HTTP call MUST have a timeout, max
  tokens/size, and bounded retries with backoff.
- Endpoints MUST be rate-limited per identity and enforce input size limits.
- Agent/tool loops MUST have an iteration cap.

---

## 11. Application security (all projects)
- **Secrets:** environment or a secret manager only. Never in code, tests,
  fixtures, logs, images, or git. `.env*` files (except `.env.example`) are
  never committed.
- **AuthN/AuthZ:** every non-public route authenticated; authorization
  checked server-side for every resource ID (no IDOR); deny by default.
  Passwords hashed with argon2/bcrypt/scrypt. Session tokens random,
  `HttpOnly`, `Secure`, `SameSite`. Constant-time comparison for secrets.
- **Input validation:** schema-validate every external input with explicit
  types and length/range limits. Reject invalid input.
- **Injection:** parameterized queries only; no shell with user input;
  no dynamic code execution; safe deserialization only (no pickle/yaml.load
  on untrusted data).
- **Paths & SSRF:** normalize paths against an allow-listed base directory;
  allow-list outbound hosts for any user-influenced URL.
- **Errors:** generic client messages; details in server logs only.
- **HTTP:** CORS restricted to known origins; CSP, X-Content-Type-Options,
  frame-ancestors, Referrer-Policy, HSTS.
- **Containers/IaC:** non-root user, minimal base image, no secrets in
  layers, least-privilege service accounts, no public buckets/DBs.
- **Crypto:** standard libraries only, no custom crypto, TLS everywhere,
  never disable certificate verification.
- **Audit:** security-relevant events (login, permission change, data
  export, admin action) are logged without sensitive payloads.

## 12. Engineering standards (all projects)
- Typed code where the language supports it (type hints, TypeScript strict).
- No swallowed exceptions, no bare catch-alls without re-raise/logging.
- No debug prints in committed code; use the project's logger.
- Every behaviour change ships with a test (including one negative/abuse
  case for security-relevant code) or a documented manual check.
- Small, reviewable diffs. No unrelated refactors in feature changes.
- Follow the existing project conventions over personal preference.

## 13. Stack mapping (examples)
| Concern | Python | Node/TS | Java/Kotlin | Go |
|---|---|---|---|---|
| Input schema | Pydantic | zod / class-validator | Bean Validation | go-playground/validator |
| SQL | SQLAlchemy params | parameterized driver / Prisma | JPA / PreparedStatement | `database/sql` placeholders |
| Password hash | argon2-cffi / bcrypt | argon2 / bcrypt | Spring Security BCrypt | x/crypto/bcrypt |
| HTML escaping | Jinja2 autoescape | framework escaping / DOMPurify | Thymeleaf / OWASP Encoder | html/template |
| Tests | pytest | vitest / jest | JUnit | `go test` |

## Severity scale (used by all agents)
| Severity | Meaning | Ship? |
|---|---|---|
| **Critical** | Exploitable now: data leak, auth bypass, RCE, secret exposure, cross-tenant access | Blocked |
| **High** | Likely exploitable, or any MUST rule violated | Blocked |
| **Medium** | Defense-in-depth gap, missing limit, weak validation, missing security test | Fix before release |
| **Low** | Hardening or quality improvement | Track |
