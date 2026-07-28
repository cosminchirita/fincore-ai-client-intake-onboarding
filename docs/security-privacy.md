# Security, privacy and auditability

## Security posture

This repository demonstrates controls; it is not a compliance certification. A real accounting deployment requires a jurisdiction-specific legal basis, data-processing agreements, records-retention policy, incident response and professional security review.

## Data classification

| Class | Examples | MVP handling |
|---|---|---|
| Public | fictional brand, service list | may appear in UI and repository |
| Internal | workflow IDs, scores, operational logs | authenticated internal access |
| Confidential | lead contact details, business volume | database only, minimized in logs |
| Highly sensitive | payroll, tax IDs, bank records, identity documents | explicitly prohibited in demo; production requires stronger controls |
| Secrets | API keys, SMTP passwords, encryption keys | environment variables; never committed |

## Threat model summary

| Threat | Control in repository | Production extension |
|---|---|---|
| Automated spam | honeypot, strict validation | WAF, rate limits, CAPTCHA/risk engine |
| SQL injection | parameterized psycopg queries | SAST/DAST and query review |
| Prompt injection | model receives data only; no tools; strict schema | content filters, model gateway and eval suite |
| Model hallucination | no invented facts rule, missing fields, Pydantic validation | confidence calibration and reviewer sampling |
| Unauthorized workflow call | internal API key | mTLS/workload identity and private network |
| Dashboard compromise | separate dashboard key | SSO, MFA, RBAC and short sessions |
| Malicious upload | extension/size checks, safe names, hashes | MIME sniffing, antivirus/CDR, quarantine and signed URLs |
| Duplicate/replayed request | idempotency key | distributed idempotency and replay monitoring |
| Lost workflow event | transactional outbox | managed queue and delivery metrics |
| Audit tampering | append-only table trigger | WORM/immutable external audit store |
| PII leakage in logs | HMAC pseudonymization and redacted interactions | centralized log redaction and DLP |
| Excess retention | `retention_until` field | scheduled erasure, legal hold and deletion evidence |
| Supply-chain compromise | minimal official images and CI | pinned digests, SBOM, signature verification, Dependabot |

## AI safety and governance

- AI output is advisory.
- The model has no database, email or document tools.
- The model cannot reject a lead, set prices, accept a client or provide professional advice.
- The prompt and model identifiers are persisted.
- The score is deterministic and versioned outside the model.
- Low confidence and sensitive language create risk flags.
- Schema failure stops the processing update.
- Real production changes to prompt/model/rules should require evaluation and approval.

## Privacy principles

### Data minimization

Only fields needed for triage are collected. Full messages are not copied into email interaction logs. AI summaries should avoid unnecessary personal detail.

### Purpose limitation

Lead data is processed only for intake, qualification support and onboarding operations. Marketing consent is separate from required privacy consent.

### Retention

Each lead receives `retention_until`, defaulting to 90 days in the demo. A production scheduled job should:

1. identify expired records not under legal hold;
2. delete or anonymize documents first;
3. remove lead PII while preserving minimal aggregate metrics where lawful;
4. create deletion evidence in an external audit system;
5. verify backups follow the same lifecycle.

### Data-subject operations

Production should implement authenticated export, correction, restriction and deletion workflows. Never fulfil a privacy request based only on an email address without identity verification.

## Supabase controls

Supabase RLS should be enabled on exposed tables. The service-role key bypasses RLS and belongs only in trusted server-side services. Browser and Streamlit clients should use authenticated user tokens with policies scoped to reviewer/admin roles. Private Storage buckets require RLS policies and signed, short-lived download URLs.

## Secrets management

The `.env` file is local-only. Production secrets should come from a managed vault and be rotated. Use different values for:

- database service credentials;
- n8n encryption key;
- internal workload identity/API key;
- dashboard/user identity;
- AI provider key;
- SMTP credentials.

Do not place secrets in exported n8n JSON, Git history, screenshots, Streamlit configuration committed to the repository or Power BI files.

## Audit event design

An audit event contains:

- UTC timestamp;
- correlation ID;
- actor type and identifier;
- action;
- resource type and ID;
- outcome;
- pseudonymized network metadata;
- minimal JSON metadata.

The database blocks updates and deletions on `audit_events`. Production should also stream events to an immutable independent destination because a database owner can still change triggers or tables.

## Security testing checklist

- unit tests for scoring boundaries and schema rejection;
- dependency and container vulnerability scanning;
- SQL/RLS policy tests;
- upload polyglot and oversized-file tests;
- authentication and authorization tests;
- prompt-injection/adversarial input suite;
- backup restore and disaster recovery exercise;
- n8n security audit;
- external penetration test before real data use.
