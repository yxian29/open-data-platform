CREATE TABLE IF NOT EXISTS lineage_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(50) NOT NULL,
    dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
    table_name VARCHAR(255),
    column_name VARCHAR(255),
    transform_name VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lineage_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id UUID REFERENCES lineage_nodes(id) ON DELETE CASCADE,
    target_node_id UUID REFERENCES lineage_nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(50) NOT NULL DEFAULT 'derives_from',
    transform_logic TEXT,
    pipeline_run_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_node_id, target_node_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_lineage_nodes_dataset ON lineage_nodes(dataset_id);
CREATE INDEX IF NOT EXISTS idx_lineage_nodes_table ON lineage_nodes(table_name);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_source ON lineage_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_target ON lineage_edges(target_node_id);
