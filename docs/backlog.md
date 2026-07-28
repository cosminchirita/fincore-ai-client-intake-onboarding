# Implementation backlog

Story points use a relative Fibonacci scale. P0 items are required for the current portfolio MVP; P1 improves credibility and production readiness; P2 demonstrates enterprise depth.

## Completed / included in repository

| Priority | Item | Points |
|---|---|---:|
| P0 | PostgreSQL schema, reporting views and fictional seed data | 5 |
| P0 | Public form and JSON intake validation | 5 |
| P0 | Transactional outbox and retry worker | 8 |
| P0 | Mock/OpenAI provider abstraction and strict schema | 8 |
| P0 | Explainable versioned scoring | 5 |
| P0 | n8n orchestration and error workflow exports | 5 |
| P0 | SMTP templates and Mailpit | 3 |
| P0 | Document metadata, hashing and upload limits | 5 |
| P0 | Streamlit reviewer dashboard | 8 |
| P0 | Audit events, privacy controls, event idempotency, tests and CI | 8 |

## Next — portfolio polish

| Priority | Item | Points | Acceptance criterion |
|---|---|---:|---|
| P0 | Add an audit timeline endpoint and dashboard tab | 5 | reviewer sees ordered events per lead |
| P0 | Add a one-command n8n workflow import script | 3 | fresh environment imports both JSON files |
| P0 | Record n8n execution success, not only errors | 3 | workflow run history includes start/success |
| P0 | Add API integration tests with ephemeral PostgreSQL | 8 | CI proves transaction and outbox behavior |
| P0 | Produce 90-second demo video and architecture image | 3 | linked from portfolio page |

## Production hardening

| Priority | Item | Points | Acceptance criterion |
|---|---|---:|---|
| P1 | SSO/MFA and reviewer RBAC | 13 | no shared dashboard key |
| P1 | Private Supabase Storage adapter | 8 | signed URLs and RLS policies tested |
| P1 | Antivirus/CDR quarantine worker | 13 | unsafe documents never reach reviewers |
| P1 | Rate limiter, reverse proxy and TLS | 8 | abuse tests and secure headers pass |
| P1 | Scheduled retention/anonymization job | 8 | deletion evidence and legal-hold exclusion |
| P1 | OpenTelemetry traces and metrics | 8 | correlation across API, worker and n8n |
| P1 | Prompt/model evaluation dataset | 13 | precision/recall and schema-failure thresholds enforced |
| P1 | Database role separation and tested RLS | 8 | API, reviewer and auditor have least privilege |
| P1 | Secret manager and automated rotation | 8 | no long-lived static keys in environment files |

## Enterprise extensions

| Priority | Item | Points |
|---|---|---:|
| P2 | Multi-tenant organization isolation | 21 |
| P2 | Kafka/SQS event bus and dedicated consumers | 21 |
| P2 | React/Next.js reviewer portal | 21 |
| P2 | CRM and accounting software connectors | 13 per connector |
| P2 | OCR/document extraction with per-field provenance | 21 |
| P2 | Human-in-the-loop correction dataset and model monitoring | 21 |
| P2 | Immutable audit archive and SIEM integration | 13 |
| P2 | Disaster recovery automation and regional failover | 21 |
| P2 | Power BI semantic model and row-level security | 13 |

## Recommended delivery sequence

1. Run and validate the included MVP.
2. Add the audit timeline and integration tests.
3. Record the portfolio demo and publish the case study.
4. Only then add one production-hardening feature that matches target freelance jobs, such as Supabase Storage or Power BI.
