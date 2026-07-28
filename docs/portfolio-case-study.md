# Portfolio case study — FinCore Accounting

## AI-powered client intake and onboarding automation

FinCore Accounting is a fictional small accounting firm used to demonstrate how a manual inquiry process can become an auditable, human-controlled workflow.

### The problem

Small professional-services firms often receive incomplete requests through website forms and email. Staff repeatedly copy information into spreadsheets, ask the same follow-up questions, decide which specialist should review the request and manually track missing documents. A basic LLM workflow can save time, but it can also introduce unreliable classifications, hidden decision logic, duplicate actions and privacy risks.

### The solution

I designed and implemented an end-to-end system that:

- validates lead data before it enters the workflow;
- commits the lead and workflow event atomically;
- uses n8n for visible orchestration;
- extracts structured facts with a zero-cost mock provider or OpenAI strict structured output;
- calculates a deterministic score with a complete criteria breakdown;
- routes missing information and qualified leads to approved email templates;
- stores documents with type/size checks, sanitized names and content hashes;
- presents a Streamlit dashboard for human review and status decisions;
- records model, prompt, scoring version, reviewer reason and operational failures.

### Architecture

The project uses FastAPI, PostgreSQL/Supabase-compatible SQL, n8n, Streamlit, Docker Compose and Mailpit. Critical rules remain in testable application code, while n8n coordinates external actions. A transactional outbox decouples public intake from workflow availability and retries failed deliveries.

### Responsible AI design

The AI model does not score the lead and cannot approve, reject, price or provide professional advice. Its output is constrained to a JSON Schema and validated again by Pydantic. Low confidence and sensitive language become visible risk flags. Human review is required before onboarding or rejection.

### Demonstrated capabilities

- AI API integration and structured outputs;
- workflow automation with n8n;
- Python/FastAPI backend development;
- PostgreSQL schema design, views, locking and RLS;
- distributed-systems reliability using an outbox pattern;
- Streamlit operational dashboard;
- privacy-aware logging and append-only audit trails;
- Docker-based local environments and CI tests;
- fintech-oriented security and human governance.

### Business value

The system demonstrates how an accounting firm could reduce repetitive triage, respond consistently, prioritize higher-fit inquiries and maintain a clear review trail without delegating sensitive client decisions to AI.

### Limitations

All data is synthetic. The project is a portfolio MVP, not an accounting platform or compliance-certified product. Production use would require SSO/MFA, private encrypted storage, malware scanning, managed secrets, formal retention workflows, monitoring, backups, legal review and integration-specific controls.
