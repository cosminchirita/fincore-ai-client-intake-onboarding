BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS n8n;

CREATE OR REPLACE FUNCTION app.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = timezone('utc', now());
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS leads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  correlation_id uuid NOT NULL DEFAULT gen_random_uuid(),
  source varchar(32) NOT NULL DEFAULT 'web_form'
    CHECK (source IN ('web_form', 'email', 'referral', 'linkedin', 'manual', 'api')),
  status varchar(32) NOT NULL DEFAULT 'received'
    CHECK (status IN (
      'received', 'processing', 'awaiting_information', 'qualified',
      'review_required', 'rejected', 'onboarding', 'active', 'archived', 'failed'
    )),
  priority varchar(16) NOT NULL DEFAULT 'unscored'
    CHECK (priority IN ('unscored', 'low', 'medium', 'high')),
  contact_name varchar(160) NOT NULL,
  company_name varchar(200) NOT NULL,
  email varchar(320) NOT NULL,
  phone varchar(40),
  country_code char(2),
  industry varchar(120),
  employee_count integer CHECK (employee_count IS NULL OR employee_count BETWEEN 1 AND 1000000),
  monthly_document_volume integer
    CHECK (monthly_document_volume IS NULL OR monthly_document_volume BETWEEN 0 AND 100000000),
  annual_revenue_band varchar(32)
    CHECK (annual_revenue_band IS NULL OR annual_revenue_band IN (
      'unknown', 'under_100k', '100k_500k', '500k_1m', '1m_5m', 'over_5m'
    )),
  requested_services text[] NOT NULL DEFAULT '{}',
  urgency varchar(16) NOT NULL DEFAULT 'normal'
    CHECK (urgency IN ('low', 'normal', 'high', 'critical')),
  message text NOT NULL,
  consent_privacy boolean NOT NULL DEFAULT false,
  consent_marketing boolean NOT NULL DEFAULT false,
  assigned_to varchar(160),
  ai_summary text,
  ai_complexity varchar(16)
    CHECK (ai_complexity IS NULL OR ai_complexity IN ('low', 'medium', 'high')),
  ai_confidence numeric(5,4) CHECK (ai_confidence IS NULL OR ai_confidence BETWEEN 0 AND 1),
  missing_information text[] NOT NULL DEFAULT '{}',
  next_action varchar(64),
  ai_model varchar(120),
  ai_prompt_version varchar(40),
  ai_processed_at timestamptz,
  retention_until date NOT NULL DEFAULT (current_date + 90),
  created_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
  updated_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
  UNIQUE (correlation_id)
);

CREATE INDEX IF NOT EXISTS idx_leads_status_created ON leads(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_priority_created ON leads(priority, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_email_lower ON leads(lower(email));
CREATE INDEX IF NOT EXISTS idx_leads_retention ON leads(retention_until);

CREATE TRIGGER trg_leads_updated_at
BEFORE UPDATE ON leads
FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();

CREATE TABLE IF NOT EXISTS lead_scores (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id uuid NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  score integer NOT NULL CHECK (score BETWEEN 0 AND 100),
  rules_version varchar(40) NOT NULL,
  breakdown jsonb NOT NULL,
  risk_flags text[] NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_lead_scores_lead_created ON lead_scores(lead_id, created_at DESC);

CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id uuid NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  original_filename varchar(255) NOT NULL,
  storage_path text NOT NULL,
  media_type varchar(160) NOT NULL,
  size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
  sha256 char(64) NOT NULL,
  document_type varchar(64) NOT NULL DEFAULT 'unclassified',
  validation_status varchar(32) NOT NULL DEFAULT 'received'
    CHECK (validation_status IN ('received', 'validated', 'rejected', 'quarantined')),
  contains_sensitive_data boolean NOT NULL DEFAULT true,
  uploaded_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
  UNIQUE (lead_id, sha256)
);
CREATE INDEX IF NOT EXISTS idx_documents_lead ON documents(lead_id, uploaded_at DESC);

CREATE TABLE IF NOT EXISTS interactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id uuid NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  channel varchar(32) NOT NULL CHECK (channel IN ('email', 'dashboard', 'api', 'n8n', 'system')),
  direction varchar(16) NOT NULL CHECK (direction IN ('inbound', 'outbound', 'internal')),
  interaction_type varchar(64) NOT NULL,
  subject varchar(255),
  content_redacted text,
  external_message_id varchar(255),
  delivery_status varchar(32) NOT NULL DEFAULT 'pending'
    CHECK (delivery_status IN ('pending', 'sent', 'delivered', 'failed', 'not_applicable')),
  created_at timestamptz NOT NULL DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_interactions_lead ON interactions(lead_id, created_at DESC);

CREATE TABLE IF NOT EXISTS workflow_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id uuid REFERENCES leads(id) ON DELETE SET NULL,
  workflow_name varchar(160) NOT NULL,
  external_execution_id varchar(255),
  status varchar(24) NOT NULL CHECK (status IN ('started', 'succeeded', 'failed', 'retrying')),
  current_step varchar(160),
  error_code varchar(80),
  error_message_redacted text,
  attempt integer NOT NULL DEFAULT 1 CHECK (attempt >= 1),
  started_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
  completed_at timestamptz
);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_lead ON workflow_runs(lead_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status, started_at DESC);

CREATE TABLE IF NOT EXISTS outbox_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  aggregate_type varchar(80) NOT NULL,
  aggregate_id uuid NOT NULL,
  event_type varchar(120) NOT NULL,
  payload jsonb NOT NULL,
  status varchar(20) NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'processing', 'delivered', 'dead_letter')),
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  available_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
  locked_at timestamptz,
  locked_by varchar(120),
  last_error_redacted text,
  delivered_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_outbox_dispatch ON outbox_events(status, available_at, created_at)
  WHERE status IN ('pending', 'processing');

CREATE TABLE IF NOT EXISTS audit_events (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  occurred_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
  correlation_id uuid,
  actor_type varchar(32) NOT NULL CHECK (actor_type IN ('anonymous', 'user', 'service', 'workflow', 'system')),
  actor_id varchar(160),
  action varchar(120) NOT NULL,
  resource_type varchar(80) NOT NULL,
  resource_id varchar(160),
  outcome varchar(24) NOT NULL CHECK (outcome IN ('success', 'denied', 'failure')),
  ip_hash char(64),
  user_agent_hash char(64),
  metadata jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_events(resource_type, resource_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_events(correlation_id, occurred_at DESC);

CREATE OR REPLACE FUNCTION app.prevent_audit_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'audit_events is append-only';
END;
$$;

CREATE TRIGGER trg_audit_no_update
BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION app.prevent_audit_mutation();

CREATE TABLE IF NOT EXISTS processed_events (
  event_id uuid PRIMARY KEY,
  lead_id uuid NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  processed_at timestamptz NOT NULL DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_processed_events_lead ON processed_events(lead_id, processed_at DESC);

CREATE TABLE IF NOT EXISTS idempotency_keys (
  key varchar(160) PRIMARY KEY,
  request_hash char(64) NOT NULL,
  response_code integer,
  response_body jsonb,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS idx_idempotency_expiry ON idempotency_keys(expires_at);

COMMIT;
