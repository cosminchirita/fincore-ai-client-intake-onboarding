# MVP definition and functional requirements

## Product statement

FinCore Intake is a demonstrable internal operations system for a fictional 5–30 person accounting firm. It reduces manual triage while preserving human accountability for client acceptance and onboarding.

## Primary actors

1. **Prospective client** — submits a request and optional synthetic documents.
2. **Accounting reviewer** — reviews classification, score and missing information; records a decision.
3. **Operations administrator** — monitors workflows, retries failures and manages configuration.
4. **Auditor/privacy reviewer** — inspects decision provenance and processing history without changing records.
5. **Service identities** — API, outbox worker and n8n, each with separate trust boundaries.

## In scope

- browser and JSON intake;
- explicit privacy consent and anti-bot honeypot;
- validation and normalization;
- asynchronous processing with reliable dispatch;
- structured AI extraction with mock and OpenAI providers;
- deterministic, explainable lead scoring;
- human-readable email templates;
- internal notification;
- document metadata, size/type controls, hashes and deduplication;
- lead pipeline dashboard and human status decisions;
- audit events, workflow failure records and correlation IDs;
- fictional seed data, local Docker deployment and automated tests.

## Out of scope for MVP

- statutory accounting, tax calculations or regulated advice;
- automated client rejection or acceptance;
- contract generation or electronic signatures;
- pricing decisions;
- real CRM/accounting platform integrations;
- OCR and document-content extraction;
- production identity provider and enterprise SSO;
- multi-tenant billing and customer portal;
- certified records retention or legal hold.

## Functional requirements

### FR-01 Intake capture

The system shall accept a lead through an HTML form and JSON API, validate field types and lengths, require privacy consent and reject populated honeypot fields.

**Acceptance:** valid intake returns HTTP 202 with a lead ID; invalid intake returns a structured 4xx response and creates no lead.

### FR-02 Atomic persistence

The API shall create the lead, append an audit event and enqueue a `lead.received` outbox event in one database transaction.

**Acceptance:** a committed lead always has a dispatchable event; a rolled-back transaction leaves neither record.

### FR-03 Reliable workflow dispatch

A worker shall claim pending events using row locks, send them to n8n, retry transient errors with exponential delay and dead-letter repeatedly failing events.

**Acceptance:** restarting the worker does not lose pending events; multiple workers do not claim the same row concurrently.

### FR-04 AI extraction

The processing endpoint shall extract industry, services, urgency, complexity, summary, missing information, next action, confidence and risk flags. Output must pass a strict schema and Pydantic validation.

**Acceptance:** unknown properties or invalid enumerations fail validation and do not update the lead.

### FR-05 Explainable scoring

The API shall calculate a 0–100 score from versioned deterministic rules, persist the complete breakdown and keep the rules independent of the LLM.

**Acceptance:** the same inputs and rules version produce the same score.

### FR-06 Human governance

No AI or score result shall automatically reject a lead, approve a contract, set a price or provide tax/legal advice.

**Acceptance:** status changes to onboarding, active, archived or rejected require an authenticated reviewer call and a recorded reason.

### FR-07 Notifications

n8n shall request an approved template based on workflow status. The API shall render and send the email through SMTP and record redacted delivery metadata.

**Acceptance:** full lead messages are not copied into interaction logs.

### FR-08 Document collection

The API shall accept allowlisted document extensions, enforce size limits, sanitize filenames, stream uploads to disk, compute SHA-256 and deduplicate per lead.

**Acceptance:** disallowed extensions receive 415; oversized files receive 413; duplicate content returns the existing logical record.

### FR-09 Dashboard

A reviewer shall see KPIs, pipeline counts, lead details, score breakdown, missing information, risk flags and document counts. A reviewer can record a status, assignee and reason.

### FR-10 Failure logging

n8n failures shall invoke an error workflow that redacts error text and sends a normalized failure event to the API.

## Non-functional requirements

- **NFR-01 Security:** secrets are environment variables; browser clients never receive service credentials.
- **NFR-02 Privacy:** synthetic data is default; PII is minimized and operational metadata is pseudonymized.
- **NFR-03 Auditability:** status and AI/scoring provenance are reconstructable.
- **NFR-04 Availability:** an unavailable n8n or email service does not prevent intake persistence.
- **NFR-05 Performance:** local intake p95 target under 500 ms excluding file upload; asynchronous processing target under 60 seconds with mock AI.
- **NFR-06 Maintainability:** business logic is unit-tested and separated from orchestration.
- **NFR-07 Portability:** local Postgres can be replaced by hosted Supabase with minimal schema change.
- **NFR-08 Accessibility:** form labels, keyboard navigation, clear errors and responsive layout are required.

## Definition of done

The MVP is complete when Docker Compose starts all services, the two n8n workflows import, a form submission reaches a scored dashboard record, Mailpit receives the expected template, a reviewer decision creates an audit event, and CI passes.
