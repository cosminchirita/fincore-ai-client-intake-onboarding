BEGIN;

CREATE OR REPLACE FUNCTION app.current_actor_role()
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(NULLIF(current_setting('request.jwt.claim.role', true), ''), 'service');
$$;

ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY leads_reviewer_read ON leads
  FOR SELECT USING (app.current_actor_role() IN ('admin', 'reviewer', 'service'));
CREATE POLICY leads_reviewer_update ON leads
  FOR UPDATE USING (app.current_actor_role() IN ('admin', 'reviewer', 'service'))
  WITH CHECK (app.current_actor_role() IN ('admin', 'reviewer', 'service'));
CREATE POLICY leads_service_insert ON leads
  FOR INSERT WITH CHECK (app.current_actor_role() IN ('admin', 'service'));

CREATE POLICY scores_reviewer_read ON lead_scores
  FOR SELECT USING (app.current_actor_role() IN ('admin', 'reviewer', 'service'));
CREATE POLICY scores_service_write ON lead_scores
  FOR ALL USING (app.current_actor_role() IN ('admin', 'service'))
  WITH CHECK (app.current_actor_role() IN ('admin', 'service'));

CREATE POLICY documents_reviewer_read ON documents
  FOR SELECT USING (app.current_actor_role() IN ('admin', 'reviewer', 'service'));
CREATE POLICY documents_service_write ON documents
  FOR ALL USING (app.current_actor_role() IN ('admin', 'service'))
  WITH CHECK (app.current_actor_role() IN ('admin', 'service'));

CREATE POLICY interactions_reviewer_read ON interactions
  FOR SELECT USING (app.current_actor_role() IN ('admin', 'reviewer', 'service'));
CREATE POLICY interactions_service_write ON interactions
  FOR ALL USING (app.current_actor_role() IN ('admin', 'service'))
  WITH CHECK (app.current_actor_role() IN ('admin', 'service'));

CREATE POLICY workflow_reviewer_read ON workflow_runs
  FOR SELECT USING (app.current_actor_role() IN ('admin', 'reviewer', 'service'));
CREATE POLICY workflow_service_write ON workflow_runs
  FOR ALL USING (app.current_actor_role() IN ('admin', 'service'))
  WITH CHECK (app.current_actor_role() IN ('admin', 'service'));

CREATE POLICY audit_admin_read ON audit_events
  FOR SELECT USING (app.current_actor_role() IN ('admin', 'auditor', 'service'));
CREATE POLICY audit_service_insert ON audit_events
  FOR INSERT WITH CHECK (app.current_actor_role() IN ('admin', 'service', 'workflow'));

COMMIT;
