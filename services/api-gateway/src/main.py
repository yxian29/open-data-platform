from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.db.postgres import get_pool, close_pool
from shared.db.minio_client import ensure_bucket
from src.routes import datasets, ontology, pipelines, auth, explorer, audit, classification, lineage, ai
from src.middleware.audit_mw import AuditMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    ensure_bucket()
    yield
    await close_pool()


app = FastAPI(
    title="Open Data Platform API",
    description="Open-source platform for semantic data integration, transformation, and analytics",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["Datasets"])
app.include_router(ontology.router, prefix="/api/v1/ontology", tags=["Ontology"])
app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["Pipelines"])
app.include_router(explorer.router, prefix="/api/v1/explorer", tags=["Data Explorer"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
app.include_router(classification.router, prefix="/api/v1/classification", tags=["Classification"])
app.include_router(lineage.router, prefix="/api/v1/lineage", tags=["Lineage"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])
app.add_middleware(AuditMiddleware)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "api-gateway"}
