# ODP — Architecture Document

## Context

Open Data Platform (ODP) is a Phase 1 MVP for semantic data integration, transformation, and analytics. It connects disparate data sources to a semantic ontology layer, enables pipeline-based transformations, and provides SQL-based analytics. This document captures the current architecture as implemented.

---

## 1. System Overview

```mermaid
graph TB
    subgraph Browser["Browser"]
        UI["React + TypeScript\nVite · TailwindCSS\nport 3000"]
    end

    subgraph Gateway["API Gateway (FastAPI · port 8000)"]
        AUTH["/auth"]
        DS["/datasets"]
        ONT["/ontology"]
        PIPE["/pipelines"]
        EXP["/explorer"]
    end

    subgraph Services["Microservices"]
        OS["Ontology Service\nFastAPI · port 8001"]
        PS["Pipeline Service\nFastAPI · port 8002"]
        DW["Dagster Webserver\nport 3100"]
        DD["Dagster Daemon\n(scheduler)"]
    end

    subgraph Storage["Data Layer"]
        PG[("PostgreSQL\nport 5432\nmetadata + state")]
        NEO[("Neo4j\nport 7687\nontology graph")]
        CH[("ClickHouse\nport 8123\nanalytics warehouse")]
        MINIO[("MinIO\nport 9000\nobject storage")]
        REDIS[("Redis\nport 6379\ncache (reserved)")]
    end

    UI -->|REST / Axios| Gateway
    ONT -->|HTTP proxy| OS
    PIPE -->|GraphQL| DW
    DS --> PG
    DS --> MINIO
    PIPE --> PG
    EXP --> CH
    OS --> NEO
    OS --> PG
    DW --> PG
    DD --> PG
    DW -.->|orchestrates| PS
    PS -->|reads| MINIO
    PS -->|writes| CH
```

---

## 2. Request Routing

```mermaid
sequenceDiagram
    participant B as Browser
    participant GW as API Gateway :8000
    participant OS as Ontology Svc :8001
    participant DW as Dagster :3100
    participant PG as PostgreSQL
    participant NEO as Neo4j
    participant MINIO as MinIO
    participant CH as ClickHouse

    Note over B,CH: Dataset Upload
    B->>GW: POST /api/v1/datasets/upload (multipart)
    GW->>GW: infer schema from first 100 rows
    GW->>MINIO: put_object datasets/{id}/{file}
    GW->>PG: INSERT INTO datasets (schema_info JSONB)
    GW-->>B: DatasetResponse

    Note over B,CH: Ontology Type Creation
    B->>GW: POST /api/v1/ontology/types
    GW->>OS: HTTP proxy → /api/v1/types
    OS->>NEO: CREATE (:ObjectType {id, name, ...})
    OS-->>B: ObjectTypeResponse

    Note over B,CH: Pipeline Trigger
    B->>GW: POST /api/v1/pipelines/{id}/run
    GW->>PG: INSERT pipeline_runs (status=running)
    GW->>DW: GraphQL launchRun(sample_pipeline)
    GW-->>B: PipelineRunResponse (status=running)
    loop Poll every 5s (background task)
        GW->>DW: GraphQL RunStatus(runId)
        DW-->>GW: SUCCESS | FAILURE | CANCELED
    end
    GW->>PG: UPDATE pipeline_runs (status=completed)

    Note over B,CH: Analytics Query
    B->>GW: POST /api/v1/explorer/query
    GW->>GW: validate SELECT-only
    GW->>CH: HTTP POST query FORMAT JSONEachRow
    CH-->>B: [{row}, {row}, ...]
```

---

## 3. Data Flow — End to End

```mermaid
flowchart LR
    subgraph Ingest["① Ingest"]
        UP["File Upload\n(CSV / JSON / Parquet)"]
        SC["Schema Inference\n(auto-detect types)"]
        UP --> SC
        SC -->|metadata| PG[("PostgreSQL\ndatasets table")]
        SC -->|raw file| MINIO[("MinIO\nodp-data/datasets/")]
    end

    subgraph Ontology["② Ontology"]
        OT["Define Object Types\n(Customer, Order…)"]
        OP["Add Properties\n(name:string, amount:float…)"]
        OL["Add Relationships\n(placed_order, one-to-many)"]
        OM["Map Dataset Columns\n→ Type Properties"]
        OT --> OP --> OL
        OT --> OM
        OT & OP & OL -->|Cypher| NEO[("Neo4j\nObjectType nodes\nLINKED_VIA edges")]
        OM -->|JSONB| PG2[("PostgreSQL\nontology_type_mappings")]
    end

    subgraph Pipeline["③ Transform"]
        DA1["Dagster Asset\nraw_datasets\n(read MinIO CSVs)"]
        DA2["Dagster Asset\ntransformed_datasets\n(clean + normalize)"]
        DA3["Dagster Asset\nanalytics_tables\n(write ClickHouse)"]
        MINIO -->|list + read| DA1
        DA1 --> DA2 --> DA3
        DA3 -->|CREATE TABLE + INSERT| CH[("ClickHouse\nodp.analytics_*\nMergeTree tables")]
    end

    subgraph Explore["④ Explore"]
        SQL["Data Explorer\n(SELECT-only SQL)"]
        CH -->|JSONEachRow| SQL
    end

    subgraph Graph["⑤ Visualize"]
        GV["Force-Directed Graph\n(react-force-graph-2d)"]
        NEO -->|Cypher MATCH| GV
    end
```

---

## 4. Neo4j Ontology Graph Model

```mermaid
graph LR
    subgraph Schema["Type Schema (authored by users)"]
        OT["(:ObjectType)\nid · name · description\nversion · created_at"]
        PT["(:PropertyType)\nid · name · data_type\nrequired · description"]
        OT -->|HAS_PROPERTY| PT
        OT -->|"LINKED_VIA\n{name, cardinality}"| OT2["(:ObjectType)"]
    end

    subgraph Instances["Object Instances (data records)"]
        OI["(:ObjectInstance)\nid · type_id · properties\nsource_dataset · created_at"]
        OI -->|"RELATES_TO\n{link_type_id}"| OI2["(:ObjectInstance)"]
    end

    OT -.->|"defines structure for"| OI

    note1["cardinality:\none-to-one\none-to-many\nmany-to-one\nmany-to-many"]
```

---

## 5. PostgreSQL Schema

```mermaid
erDiagram
    datasets {
        uuid id PK
        varchar name
        text description
        varchar source_type
        text storage_path
        jsonb schema_info
        bigint row_count
        bigint file_size_bytes
        varchar created_by
        timestamptz created_at
        timestamptz updated_at
    }

    ontology_type_mappings {
        uuid id PK
        varchar object_type_id
        uuid dataset_id FK
        jsonb column_mappings
        varchar sync_strategy
        timestamptz last_synced_at
        timestamptz created_at
    }

    pipeline_definitions {
        uuid id PK
        varchar name
        text description
        varchar pipeline_type
        jsonb config
        varchar schedule
        varchar created_by
        timestamptz created_at
        timestamptz updated_at
    }

    pipeline_runs {
        uuid id PK
        uuid pipeline_id FK
        varchar status
        timestamptz started_at
        timestamptz completed_at
        text logs
        text error
        timestamptz created_at
    }

    audit_log {
        uuid id PK
        varchar user_id
        varchar action
        varchar resource_type
        varchar resource_id
        jsonb details
        timestamptz created_at
    }

    datasets ||--o{ ontology_type_mappings : "mapped to"
    pipeline_definitions ||--o{ pipeline_runs : "has runs"
```

---

## 6. Dagster Pipeline DAG

```mermaid
flowchart LR
    subgraph MinIO["MinIO odp-data/"]
        CSV["datasets/\n{uuid}/\n*.csv"]
    end

    subgraph Dagster["Dagster · sample_pipeline (cron: 0 */6 * * *)"]
        A1["raw_datasets\nread all CSVs\nreturn Dict[name→DataFrame]"]
        A2["transformed_datasets\ndrop nulls · normalize cols\nstrip whitespace"]
        A3["analytics_tables\ninfer CH types\nCREATE TABLE IF NOT EXISTS\nINSERT CSVWithNames"]
        A1 --> A2 --> A3
    end

    subgraph ClickHouse["ClickHouse · odp database"]
        T1["analytics_customers\nMergeTree()"]
        T2["analytics_orders\nMergeTree()"]
        T3["analytics_products\nMergeTree()"]
    end

    CSV -->|Minio client| A1
    A3 -->|HTTP POST| T1 & T2 & T3

    style A1 fill:#e67e22,color:#fff
    style A2 fill:#e67e22,color:#fff
    style A3 fill:#e67e22,color:#fff
```

---

## 7. Frontend Page → API Mapping

```mermaid
graph LR
    subgraph Pages["React Pages"]
        DASH["Dashboard"]
        DS["Datasets"]
        ONT["Ontology\nExplorer"]
        PIPE["Pipelines"]
        EXP["Data\nExplorer"]
    end

    subgraph API["API Gateway /api/v1"]
        A1["/datasets\n(list, upload,\npreview, delete)"]
        A2["/ontology/types\n(CRUD + properties\n+ links + map)"]
        A3["/ontology/graph\n(nodes + edges)"]
        A4["/ontology/objects\n(instances + neighbors)"]
        A5["/pipelines\n(CRUD + run + runs)"]
        A6["/explorer/query\n(SELECT only)"]
    end

    DASH --> A1 & A2 & A5
    DS --> A1
    ONT --> A2 & A3 & A4 & A1
    PIPE --> A5
    EXP --> A6
```

---

## 8. Authentication & Authorization

```mermaid
flowchart TD
    REQ["Incoming Request"]
    JWT{"Bearer token\npresent?"}
    VAL{"Valid JWT?\n(HS256)"}
    ANON["Anonymous\nrole = viewer"]
    USER["Authenticated\nrole = admin|analyst|viewer"]
    RBAC{"Role check\nrequired?"}
    HIER["Hierarchy:\nadmin=3 > analyst=2 > viewer=1"]
    ALLOW["Allow"]
    DENY["403 Forbidden"]

    REQ --> JWT
    JWT -->|No| ANON --> RBAC
    JWT -->|Yes| VAL
    VAL -->|Invalid| ANON
    VAL -->|Valid| USER --> RBAC
    RBAC -->|No auth needed| ALLOW
    RBAC -->|Yes| HIER
    HIER -->|Sufficient role| ALLOW
    HIER -->|Insufficient role| DENY
```

**Demo credentials:** `admin/admin` · `analyst/analyst` · `viewer/viewer`

---

## 9. Storage Responsibility Matrix

| Store | What lives there | Access pattern |
|---|---|---|
| **PostgreSQL** | Dataset metadata, pipeline definitions + runs, ontology-dataset mappings, audit log | Async/await via asyncpg pool (2–10 connections) |
| **Neo4j** | ObjectType nodes, PropertyType nodes, LINKED_VIA edges, ObjectInstance nodes, RELATES_TO edges | Async Cypher via neo4j-python-driver |
| **MinIO** | Raw uploaded files (`datasets/{uuid}/{filename}`) | S3-compatible SDK; read by Dagster asset |
| **ClickHouse** | Transformed analytics tables (`analytics_{name}`) | HTTP REST, JSONEachRow format |
| **Redis** | Reserved — configured but not yet used | — |

---

## 10. Inter-Service Communication

```mermaid
graph TD
    GW["API Gateway :8000"]
    OS["Ontology Svc :8001"]
    DW["Dagster :3100"]

    GW -->|"HTTP proxy (httpx, timeout 30s)\nall /ontology/* routes"| OS
    GW -->|"GraphQL HTTP\nlaunchRun mutation\nRunStatus query"| DW

    GW -->|asyncpg| PG[("PostgreSQL")]
    OS -->|asyncpg| PG
    OS -->|"async Cypher"| NEO[("Neo4j")]
    DW -->|asyncpg| PG
    DW -->|"Minio SDK"| MINIO[("MinIO")]
    DW -->|"HTTP POST\nCSVWithNames"| CH[("ClickHouse")]
    GW -->|"HTTP POST\nJSONEachRow"| CH
    GW -->|"Minio SDK"| MINIO
```

---

## 11. Key Design Decisions

| Decision | Rationale |
|---|---|
| API Gateway proxies to Ontology Service | Keeps ontology logic isolated; single ingress for clients |
| Neo4j for ontology | Natural fit for graph-shaped schema (types + relationships); Cypher traversal for neighbors |
| ClickHouse for analytics | Columnar, sub-second aggregations, MergeTree handles append-only analytics tables |
| MinIO for raw files | S3-compatible, runs locally, decoupled from DB |
| Dagster for orchestration | Software-defined assets model, built-in lineage, web UI for monitoring |
| dbt for transforms | SQL-native, self-documenting models, view/table materialization strategy |
| PostgreSQL for metadata | Relational integrity for pipeline runs + mappings; JSONB for flexible schemas |
| Async throughout | asyncpg + neo4j async driver + httpx — FastAPI handles concurrent requests efficiently |

---

## 12. Infrastructure Init

```mermaid
sequenceDiagram
    participant make as make up
    participant DC as docker-compose
    participant PG as PostgreSQL
    participant CH as ClickHouse
    participant GW as API Gateway

    make->>DC: docker compose up -d --build
    DC->>PG: start + run init-scripts/00-init.sql
    Note over PG: creates: datasets, ontology_type_mappings,<br/>pipeline_definitions, pipeline_runs, audit_log
    DC->>CH: start + run clickhouse-init/00-create-database.sql
    Note over CH: CREATE DATABASE IF NOT EXISTS odp
    DC->>GW: start (waits for PG, MinIO, Redis, Neo4j, CH healthy)
    GW->>GW: ensure_bucket() → creates odp-data in MinIO
    GW->>GW: ready

    Note over make: make seed → python3 examples/seed.py
    Note over make: Uploads customers/orders/products CSVs<br/>Creates Customer/Order/Product ontology types<br/>Creates sample ETL pipeline definition
```

---

## Verification

To verify the full system after `make up && make seed`:

1. `curl http://localhost:8000/health` → `{"status":"healthy"}`
2. Upload a CSV → appears in Datasets page and MinIO bucket
3. Create an ObjectType in Ontology Explorer → node appears in force graph
4. Add a relationship → edge appears with label and animated particles
5. Trigger pipeline from Pipelines page → status transitions running → completed
6. Query `SELECT COUNT(*) FROM analytics_customers` in Data Explorer → returns row count
7. `curl http://localhost:8123/?database=odp&user=default&password=clickhouse_secret --data "SHOW TABLES"` → lists analytics_* tables
