BEGIN;

CREATE OR REPLACE VIEW lead_latest_scores WITH (security_invoker = true) AS
SELECT DISTINCT ON (lead_id)
  lead_id, score, rules_version, breakdown, risk_flags, created_at
FROM lead_scores
ORDER BY lead_id, created_at DESC;

CREATE OR REPLACE VIEW dashboard_leads WITH (security_invoker = true) AS
SELECT
  l.id,
  l.created_at,
  l.updated_at,
  l.status,
  l.priority,
  l.company_name,
  l.contact_name,
  l.email,
  l.industry,
  l.employee_count,
  l.monthly_document_volume,
  l.requested_services,
  l.urgency,
  l.ai_summary,
  l.ai_complexity,
  l.ai_confidence,
  l.missing_information,
  l.next_action,
  s.score,
  s.breakdown,
  s.risk_flags,
  (SELECT count(*) FROM documents d WHERE d.lead_id = l.id) AS document_count,
  (SELECT max(i.created_at) FROM interactions i WHERE i.lead_id = l.id) AS last_interaction_at
FROM leads l
LEFT JOIN lead_latest_scores s ON s.lead_id = l.id;

CREATE OR REPLACE VIEW dashboard_kpis WITH (security_invoker = true) AS
SELECT
  count(*) AS total_leads,
  count(*) FILTER (WHERE created_at >= timezone('utc', now()) - interval '7 days') AS leads_last_7_days,
  count(*) FILTER (WHERE status = 'qualified') AS qualified_leads,
  count(*) FILTER (WHERE status = 'review_required') AS review_required,
  count(*) FILTER (WHERE status = 'awaiting_information') AS awaiting_information,
  count(*) FILTER (WHERE priority = 'high') AS high_priority,
  round(avg(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60.0)::numeric, 2) AS avg_processing_minutes
FROM leads;

COMMIT;
