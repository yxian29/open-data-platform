from fastapi import FastAPI

app = FastAPI(
    title="Open Data Platform Pipeline Service",
    version="0.1.0",
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "pipeline-service"}
