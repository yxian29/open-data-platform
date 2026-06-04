ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS ip_address INET;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_agent TEXT;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'success';
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS duration_ms INTEGER;

CREATE TABLE IF NOT EXISTS audit_retention_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(100) NOT NULL UNIQUE,
    retention_days INTEGER NOT NULL DEFAULT 90,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO audit_retention_policies (resource_type, retention_days) VALUES
    ('dataset', 90),
    ('pipeline', 90),
    ('ontology', 90),
    ('auth', 365),
    ('classification', 90),
    ('connector', 90)
ON CONFLICT (resource_type) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_audit_log_user_action ON audit_log(user_id, action);
CREATE INDEX IF NOT EXISTS idx_audit_log_session ON audit_log(session_id);
