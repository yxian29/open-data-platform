# Open Data Platform — POC Implementation Plan

## Context

**Goal**: Build a product/startup — an open-source semantic data platform. This is a full Phase 1 MVP with all core services running locally via Docker Compose.

**What ODP does**: Enterprise data platform that connects disparate data sources, maps them to a semantic "Ontology" (business objects + relationships), enables pipeline-based transformations, enforces governance/lineage, and provides analytics + AI-powered insights.

**Why build this**: There is no credible open-source alternative that combines data integration, ontology, pipelines, governance, and AI in one cohesive platform.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│  FRONTEND: React + TypeScript + TailwindCSS              │
├──────────────────────────────────────────────────────────┤
│  API GATEWAY: FastAPI (REST + GraphQL via Strawberry)     │
├──────────────────────────────────────────────────────────┤
│  SERVICES (all Python/FastAPI):                          │
│  - Ontology Service (Neo4j-backed)                       │
│  - Pipeline Service (Dagster + dbt)                      │
│  - Governance Service (lineage, audit, RBAC)             │
│  - AI Service (LangChain + Qdrant) [Phase 3]            │
│  - Actions Service (triggers/webhooks) [Phase 4]         │
├──────────────────────────────────────────────────────────┤
│  ORCHESTRATION: Dagster                                  │
├──────────────────────────────────────────────────────────┤
│  DATA: Airbyte (ingest) + dbt (transform) + Spark (heavy)│
├──────────────────────────────────────────────────────────┤
│  STORAGE: PostgreSQL | MinIO | ClickHouse | Neo4j | Redis│
├──────────────────────────────────────────────────────────┤
│  INFRA: Docker Compose + Traefik (reverse proxy)         │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 1 — MVP Foundation (4-6 weeks)

### Week 1: Infrastructure + API Gateway

**Docker Compose Infrastructure:**
- PostgreSQL 15 — metadata, catalog, audit logs
- MinIO — S3-compatible object storage for raw data files
- Redis 7 — caching, session management, event pub/sub
- Neo4j 5 — ontology graph database
- ClickHouse — OLAP analytics engine for fast queries
- Traefik — reverse proxy, auto-discovers Docker services

**API Gateway (FastAPI):**
- `services/api-gateway/src/main.py` — FastAPI app with CORS, health check
- JWT-based authentication (simple, no Keycloak yet)
- Route modules for datasets, ontology, pipelines
- Shared library: Pydantic models, DB clients (asyncpg, neo4j-driver, minio-py), config

**Files to create:**
```
docker-compose.yml
docker-compose.override.yml
.env.example
Makefile
services/api-gateway/Dockerfile
services/api-gateway/pyproject.toml
services/api-gateway/src/main.py
services/api-gateway/src/routes/__init__.py
services/api-gateway/src/middleware/auth.py
shared/models/__init__.py
shared/db/postgres.py
shared/db/neo4j.py
shared/db/minio.py
shared/config.py
infrastructure/init-scripts/00-init.sql
infrastructure/traefik/traefik.yml
```

---

### Week 2: Data Ingestion Service

**Functionality:**
- `POST /api/v1/datasets/upload` — accepts CSV/JSON/Parquet, stores in MinIO, infers schema, registers in Postgres catalog
- `GET /api/v1/datasets` — list all datasets with metadata
- `GET /api/v1/datasets/{id}` — dataset details + inferred schema
- `GET /api/v1/datasets/{id}/preview` — first N rows as JSON
- `DELETE /api/v1/datasets/{id}` — remove from catalog + MinIO

**Schema inference:** automatically detect column names, data types, and nullability from sample data.

**Data model (PostgreSQL):**
```sql
CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_type VARCHAR(50) NOT NULL,  -- 'csv', 'json', 'parquet', 'api'
    storage_path TEXT NOT NULL,         -- MinIO object key
    schema JSONB,                       -- inferred column schema
    row_count BIGINT,
    file_size_bytes BIGINT,
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Files to create:**
```
services/api-gateway/src/routes/datasets.py
shared/models/dataset.py
infrastructure/init-scripts/01-datasets.sql
```

---

### Week 3: Ontology Service

**What the Ontology does:** Creates a semantic layer over raw data. Maps physical tables/files to logical business objects (e.g., "Customer", "Order", "Product") with typed properties and relationships between them. This is the core differentiator of the platform.

**Neo4j data model:**
```cypher
// Type definitions (schema)
(:ObjectType {id: UUID, name: String, description: String, version: Int})
(:PropertyType {id: UUID, name: String, data_type: String, required: Boolean})
(:LinkType {id: UUID, name: String, cardinality: String, description: String})

// Schema relationships
(:ObjectType)-[:HAS_PROPERTY]->(:PropertyType)
(:ObjectType)-[:LINKED_VIA {link_type_id: UUID}]->(:ObjectType)

// Instance data (actual objects)
(:ObjectInstance {id: UUID, type_id: UUID, properties: Map, source_dataset: String})
(:ObjectInstance)-[:RELATES_TO {link_type_id: UUID}]->(:ObjectInstance)
```

**API endpoints:**
- `POST /api/v1/ontology/types` — create object type (e.g., "Customer")
- `GET /api/v1/ontology/types` — list all object types
- `POST /api/v1/ontology/types/{id}/properties` — add property to type
- `POST /api/v1/ontology/types/{id}/links` — define relationship to another type
- `POST /api/v1/ontology/types/{id}/map` — map a dataset to this object type (columns -> properties)
- `GET /api/v1/ontology/objects` — query object instances (filter by type, properties)
- `GET /api/v1/ontology/objects/{id}/neighbors` — traverse relationships
- `GET /api/v1/ontology/graph` — get full type graph for visualization

**Key design:** The ontology is a **virtual layer** — it doesn't duplicate data. Object instances reference rows in source datasets. Neo4j stores the graph structure, while property values come from the underlying storage (ClickHouse/Postgres).

**Files to create:**
```
services/ontology/Dockerfile
services/ontology/pyproject.toml
services/ontology/src/main.py
services/ontology/src/routes/types.py
services/ontology/src/routes/objects.py
services/ontology/src/routes/links.py
services/ontology/src/graph.py
shared/models/ontology.py
```

---

### Week 4: Pipeline Service (Dagster + dbt)

**What Pipelines do:** Define and execute data transformation workflows. Raw data from ingestion gets cleaned, enriched, aggregated, and loaded into analytics tables.

**Components:**
- Dagster — orchestrates pipeline execution, scheduling, monitoring
- dbt-core — SQL-based transformations with built-in testing and documentation

**Docker additions:**
- `dagster-webserver` — pipeline UI (accessible at `/pipelines-ui`)
- `dagster-daemon` — scheduler and sensor execution

**API endpoints:**
- `POST /api/v1/pipelines` — register a pipeline definition
- `GET /api/v1/pipelines` — list pipelines
- `POST /api/v1/pipelines/{id}/run` — trigger execution
- `GET /api/v1/pipelines/{id}/runs` — list runs with status
- `GET /api/v1/pipelines/{id}/runs/{run_id}/logs` — execution logs

**Sample pipeline (end-to-end demo):**
1. CSV uploaded via datasets API -> stored in MinIO
2. Dagster asset reads CSV from MinIO
3. dbt model cleans/transforms the data (dedup, type casting, aggregations)
4. Results loaded into ClickHouse analytics table
5. Ontology objects updated/created from transformed data

**Files to create:**
```
services/pipelines/Dockerfile
services/pipelines/pyproject.toml
services/pipelines/src/main.py
services/pipelines/src/routes/pipelines.py
services/pipelines/dagster/workspace.yaml
services/pipelines/dagster/definitions.py
services/pipelines/dbt/dbt_project.yml
services/pipelines/dbt/profiles.yml
services/pipelines/dbt/models/staging/stg_sample.sql
services/pipelines/dbt/models/marts/mart_sample.sql
shared/models/pipeline.py
```

---

### Weeks 5-6: React Frontend

**Tech stack:** React 18, TypeScript, TailwindCSS, React Router v6, Tanstack Query, react-force-graph

**Pages:**

| Page | Description |
|------|-------------|
| **Dashboard** | Overview cards: dataset count, object types, recent pipeline runs, system health |
| **Datasets** | Drag-drop file upload, dataset table, schema viewer, data preview modal |
| **Ontology Explorer** | Force-directed graph visualization of object types + relationships. Click a node to inspect properties and instances |
| **Pipelines** | Pipeline list, run history table, trigger button, real-time log viewer |
| **Data Explorer** | SQL editor (CodeMirror) connected to ClickHouse, results as sortable table |

**Files to create:**
```
frontend/package.json
frontend/tsconfig.json
frontend/tailwind.config.js
frontend/vite.config.ts
frontend/Dockerfile
frontend/src/App.tsx
frontend/src/pages/Dashboard.tsx
frontend/src/pages/Datasets.tsx
frontend/src/pages/OntologyExplorer.tsx
frontend/src/pages/Pipelines.tsx
frontend/src/pages/DataExplorer.tsx
frontend/src/components/Layout.tsx
frontend/src/components/FileUpload.tsx
frontend/src/components/DataTable.tsx
frontend/src/components/GraphViewer.tsx
frontend/src/api/client.ts
```

---

## Full Project Structure

```
palantir-poc/
├── docker-compose.yml
├── docker-compose.override.yml
├── .env.example
├── Makefile
├── README.md
├── PLAN.md
│
├── services/
│   ├── api-gateway/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── src/
│   │       ├── main.py
│   │       ├── routes/
│   │       │   ├── __init__.py
│   │       │   ├── datasets.py
│   │       │   ├── ontology.py
│   │       │   └── pipelines.py
│   │       ├── middleware/
│   │       │   └── auth.py
│   │       └── schemas/
│   │
│   ├── ontology/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── src/
│   │       ├── main.py
│   │       ├── routes/
│   │       │   ├── types.py
│   │       │   ├── objects.py
│   │       │   └── links.py
│   │       └── graph.py
│   │
│   └── pipelines/
│       ├── Dockerfile
│       ├── pyproject.toml
│       ├── src/
│       │   ├── main.py
│       │   └── routes/
│       │       └── pipelines.py
│       ├── dagster/
│       │   ├── workspace.yaml
│       │   └── definitions.py
│       └── dbt/
│           ├── dbt_project.yml
│           ├── profiles.yml
│           └── models/
│               ├── staging/
│               └── marts/
│
├── shared/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── dataset.py
│   │   ├── ontology.py
│   │   ├── pipeline.py
│   │   └── user.py
│   └── db/
│       ├── __init__.py
│       ├── postgres.py
│       ├── neo4j.py
│       └── minio.py
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── Datasets.tsx
│       │   ├── OntologyExplorer.tsx
│       │   ├── Pipelines.tsx
│       │   └── DataExplorer.tsx
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── FileUpload.tsx
│       │   ├── DataTable.tsx
│       │   └── GraphViewer.tsx
│       └── api/
│           └── client.ts
│
├── infrastructure/
│   ├── init-scripts/
│   │   ├── 00-init.sql
│   │   └── 01-datasets.sql
│   ├── traefik/
│   │   └── traefik.yml
│   └── docker/
│
├── examples/
│   └── sample-data/
│       ├── customers.csv
│       ├── orders.csv
│       └── products.csv
│
└── docs/
    └── architecture.md
```

---

## Technology Choices

| Layer | Technology | Why |
|-------|-----------|-----|
| **API** | FastAPI | Async, auto-docs (OpenAPI), type-safe with Pydantic, Python ecosystem fit |
| **GraphQL** | Strawberry | Type-safe Python GraphQL, integrates natively with FastAPI |
| **Graph DB** | Neo4j 5 Community | Best graph database, Cypher query language, natural fit for ontology |
| **Orchestration** | Dagster | Software-defined assets model, built-in lineage, better DX than Airflow |
| **Transforms** | dbt-core | Industry standard SQL transforms, testable, self-documenting |
| **Object Storage** | MinIO | S3-compatible, runs locally, battle-tested |
| **OLAP** | ClickHouse | Sub-second analytics queries, columnar storage, excellent for dashboards |
| **Metadata DB** | PostgreSQL 15 | Reliable, JSONB for flexible schemas, excellent async drivers |
| **Cache/Events** | Redis 7 | Caching, session management, Streams for lightweight event bus |
| **Frontend** | React 18 + TypeScript + Tailwind | Standard modern web stack, rich component ecosystem |
| **Graph Viz** | react-force-graph | Interactive force-directed graphs, WebGL performance |
| **Reverse Proxy** | Traefik | Auto-discovers Docker services, simple YAML config |
| **Build Tool** | Vite | Fast HMR, native TypeScript support |

---

## Future Phases (designed for, not building now)

### Phase 2 — Governance & Connectors (3-4 weeks)
- Keycloak for enterprise RBAC (OIDC/SAML)
- Airbyte integration for 300+ external source connectors
- Column-level data lineage tracking
- Audit trail service (who accessed what, when)
- Data classification and marking system
- dbt tests and documentation

### Phase 3 — Analytics & AI (3-4 weeks)
- Apache Superset for dashboards and BI
- AI/LLM service (LangChain + Qdrant)
  - Natural language to SQL (text-to-SQL)
  - Ontology-aware question answering (RAG)
  - Schema suggestion for new datasets
  - Data summarization
- Streamlit notebooks for ad-hoc analysis
- GraphQL endpoint for ontology traversal

### Phase 4 — Operations & Scale (2-3 weeks)
- Actions/triggers engine (data conditions -> webhooks/notifications)
- Kubernetes deployment manifests (Helm charts)
- Python SDK for programmatic access
- Monitoring stack (Prometheus + Grafana)
- Data quality monitoring and alerting
- Multi-tenant support

---

## Verification Plan

| Step | What to verify |
|------|---------------|
| 1 | `make up` — all containers start healthy (`docker ps` shows all green) |
| 2 | Upload a CSV via the UI -> appears in MinIO bucket and datasets catalog |
| 3 | Define an ObjectType "Customer" with properties -> visible in Neo4j |
| 4 | Map the uploaded CSV to the Customer type -> object instances created |
| 5 | Trigger a pipeline -> Dagster runs dbt transforms -> data lands in ClickHouse |
| 6 | Query ClickHouse from Data Explorer -> results display correctly |
| 7 | View ontology graph in UI -> nodes and edges render, click to inspect |
| 8 | `make test` — all service unit tests pass |

---

## Resource Requirements

| Profile | RAM | What's running |
|---------|-----|---------------|
| `minimal` | ~8 GB | Postgres, MinIO, Redis, Neo4j, API gateway |
| `standard` | ~12 GB | + ClickHouse, Dagster, frontend |
| `full` | ~16 GB+ | + all services, sample data loaded |

---

## Quick Start (target experience)

```bash
git clone <repo>
cd palantir-poc
cp .env.example .env
make up          # starts all services
make seed        # loads sample data (customers, orders, products)
# Open http://localhost:3000 for the UI
# Open http://localhost:3000/pipelines-ui for Dagster
```
