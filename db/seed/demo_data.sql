BEGIN;

INSERT INTO leads (
  id, source, status, priority, contact_name, company_name, email, country_code,
  industry, employee_count, monthly_document_volume, annual_revenue_band,
  requested_services, urgency, message, consent_privacy, ai_summary,
  ai_complexity, ai_confidence, missing_information, next_action, ai_model,
  ai_prompt_version, ai_processed_at
) VALUES
(
  '11111111-1111-4111-8111-111111111111', 'web_form', 'qualified', 'high',
  'Elena Popescu', 'Northstar Commerce SRL', 'elena.popescu@example.com', 'RO',
  'ecommerce', 18, 1200, '1m_5m', ARRAY['accounting','payroll','cash_flow_reporting'],
  'high', 'We operate an online shop with 18 employees and need monthly accounting, payroll and cash-flow reporting.',
  true, 'Growing ecommerce company requesting accounting, payroll and cash-flow reporting.',
  'high', 0.94, ARRAY[]::text[], 'schedule_discovery_call', 'mock-rules-v1', 'lead-extraction-v1', timezone('utc', now())
),
(
  '22222222-2222-4222-8222-222222222222', 'referral', 'awaiting_information', 'medium',
  'Mihai Ionescu', 'Atlas Design Studio SRL', 'mihai.ionescu@example.com', 'RO',
  'professional_services', 6, 120, '100k_500k', ARRAY['accounting'],
  'normal', 'We are looking for a new accounting partner starting next quarter.',
  true, 'Small design studio seeking accounting services; key volume and deadline details are missing.',
  'medium', 0.82, ARRAY['current accounting software','monthly transaction count'],
  'request_missing_information', 'mock-rules-v1', 'lead-extraction-v1', timezone('utc', now())
),
(
  '33333333-3333-4333-8333-333333333333', 'email', 'review_required', 'low',
  'Andrei Marin', 'Solo Advisory PFA', 'andrei.marin@example.com', 'RO',
  'consulting', 1, 20, 'under_100k', ARRAY['tax_advisory'],
  'low', 'I need occasional advice on taxes for a sole proprietorship.',
  true, 'Sole proprietor requesting occasional tax advisory.',
  'low', 0.77, ARRAY['budget','preferred engagement model'], 'manual_review',
  'mock-rules-v1', 'lead-extraction-v1', timezone('utc', now())
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO lead_scores (lead_id, score, rules_version, breakdown, risk_flags)
VALUES
('11111111-1111-4111-8111-111111111111', 91, '2026-01',
 '{"data_completeness":15,"service_fit":20,"volume_fit":15,"urgency":10,"industry_fit":10,"document_readiness":10,"commercial_fit":16,"risk_penalty":-5}', ARRAY['human_review_before_contract']),
('22222222-2222-4222-8222-222222222222', 63, '2026-01',
 '{"data_completeness":8,"service_fit":20,"volume_fit":8,"urgency":5,"industry_fit":10,"document_readiness":2,"commercial_fit":10,"risk_penalty":0}', ARRAY[]::text[]),
('33333333-3333-4333-8333-333333333333', 39, '2026-01',
 '{"data_completeness":8,"service_fit":12,"volume_fit":2,"urgency":2,"industry_fit":8,"document_readiness":2,"commercial_fit":5,"risk_penalty":0}', ARRAY[]::text[])
ON CONFLICT DO NOTHING;

INSERT INTO audit_events (correlation_id, actor_type, actor_id, action, resource_type, resource_id, outcome, metadata)
SELECT correlation_id, 'system', 'demo-seed', 'lead.seeded', 'lead', id::text, 'success', '{"synthetic":true}'::jsonb
FROM leads WHERE id IN (
  '11111111-1111-4111-8111-111111111111',
  '22222222-2222-4222-8222-222222222222',
  '33333333-3333-4333-8333-333333333333'
);

COMMIT;
