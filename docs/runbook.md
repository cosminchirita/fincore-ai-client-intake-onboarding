# Operations runbook

## Service inventory

| Service | Port | Health signal |
|---|---:|---|
| API | 8000 | `GET /health` returns 200 |
| Dashboard | 8501 | page loads and API calls succeed |
| n8n | 5678 | UI available; workflow active |
| Mailpit UI | 8025 | web UI available |
| Mailpit SMTP | 1025 | API can deliver test email |
| PostgreSQL | 5432 | `pg_isready` succeeds |

## Startup

```bash
cp .env.example .env
# replace local secrets
docker compose up --build -d
docker compose ps
docker compose logs --tail=200 api worker n8n
```

Create the n8n owner account, import workflows and activate them. Verify the worker URL and webhook path match.

## Smoke test

```bash
curl -fsS http://localhost:8000/health
python scripts/send_demo_lead.py
```

Expected outcome within approximately one minute in mock mode:

- lead appears in Streamlit;
- n8n execution succeeds;
- lead has a score and summary;
- Mailpit receives an internal notification and, where applicable, a client template.

## Failure scenarios

### Lead remains `received`

1. inspect worker logs;
2. check n8n is running and intake workflow is active;
3. verify `N8N_WEBHOOK_URL` and `INTERNAL_API_KEY`;
4. inspect `outbox_events` status and `last_error_redacted`;
5. reactivate the event only after fixing the root cause.

### n8n receives 401

The key in the n8n container does not match the API `INTERNAL_API_KEY`. Rotate and restart both services.

### AI processing fails

- for local demonstration, set `AI_PROVIDER=mock`;
- for OpenAI, verify key, model access, timeout and schema compatibility;
- inspect `workflow_runs` and API logs;
- never fall back to unvalidated free-form JSON.

### Email fails

- verify Mailpit/SMTP connectivity;
- confirm sender configuration;
- check the interaction record has `failed` delivery status;
- retry from n8n after connectivity is restored.

### Upload rejected

- 413: file exceeds `MAX_UPLOAD_MB`;
- 415: extension is outside the allowlist;
- duplicate: the same SHA-256 already exists for the lead;
- production malware quarantine is not implemented in this demo.

## Dead-letter recovery

Query:

```sql
SELECT id, aggregate_id, event_type, attempts, last_error_redacted
FROM outbox_events
WHERE status = 'dead_letter'
ORDER BY created_at;
```

After root-cause remediation, reset a specific event:

```sql
UPDATE outbox_events
SET status = 'pending', attempts = 0, available_at = timezone('utc', now()),
    last_error_redacted = NULL, locked_at = NULL, locked_by = NULL
WHERE id = '<event-uuid>' AND status = 'dead_letter';
```

Record operator identity and reason in the audit system in production.

## Backup and restore

Local backup example:

```bash
docker compose exec -T db pg_dump -U fincore -d fincore -Fc > fincore-demo.dump
```

A backup is not valid until restored and verified in an isolated environment. Production targets should include point-in-time recovery and encrypted object-storage backup lifecycle.

## Observability and SLOs

Suggested production SLIs:

- intake API availability;
- p95 intake latency;
- outbox oldest-pending age;
- workflow success rate;
- AI schema-validation failure rate;
- email delivery failure rate;
- manual review queue age;
- expired-retention records awaiting deletion.

Suggested initial SLOs for a small deployment:

- API monthly availability: 99.5%;
- 99% of committed outbox events delivered within 5 minutes;
- 95% of mock-mode leads scored within 60 seconds;
- zero automated contract/price/rejection decisions;
- zero secrets in repository and exported workflows.

## Incident priorities

- **P0:** unauthorized data access, secret exposure, destructive corruption.
- **P1:** intake unavailable, events permanently stuck, widespread incorrect routing.
- **P2:** dashboard degraded, delayed emails, individual workflow errors.
- **P3:** cosmetic/reporting issue without data integrity impact.
