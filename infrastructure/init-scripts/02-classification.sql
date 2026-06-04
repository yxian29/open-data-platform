DO $$ BEGIN
    CREATE TYPE classification_level AS ENUM ('public', 'internal', 'confidential', 'restricted');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS data_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    column_name VARCHAR(255),
    classification classification_level NOT NULL DEFAULT 'internal',
    reason TEXT DEFAULT '',
    classified_by VARCHAR(255) DEFAULT 'system',
    classified_at TIMESTAMPTZ DEFAULT NOW(),
    auto_detected BOOLEAN DEFAULT FALSE,
    UNIQUE(dataset_id, column_name)
);

CREATE TABLE IF NOT EXISTS classification_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    pattern VARCHAR(500) NOT NULL,
    match_type VARCHAR(20) NOT NULL DEFAULT 'column_name',
    classification classification_level NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO classification_rules (name, pattern, classification) VALUES
    ('SSN Pattern', '(?i)(ssn|social.?security)', 'restricted'),
    ('Email Column', '(?i)(email|e.?mail)', 'confidential'),
    ('Phone Column', '(?i)(phone|mobile|cell)', 'confidential'),
    ('Password Field', '(?i)(password|passwd|pwd)', 'restricted'),
    ('PII Name', '(?i)(first.?name|last.?name|full.?name)', 'confidential'),
    ('Address', '(?i)(address|street|zip.?code|postal)', 'confidential'),
    ('ID Columns', '(?i)^id$|_id$', 'internal')
ON CONFLICT DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_classifications_dataset ON data_classifications(dataset_id);
CREATE INDEX IF NOT EXISTS idx_classifications_level ON data_classifications(classification);
