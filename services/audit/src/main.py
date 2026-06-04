from contextlib import asynccontextmanager

from fastapi import FastAPI

from shared.db.postgres import get_pool, close_pool
from src.routes import events, retention, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(
    title="ODP Audit Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(retention.router, prefix="/api/v1/retention", tags=["Retention"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["Stats"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "audit-service"}
