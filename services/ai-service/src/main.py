from fastapi import FastAPI

from src.routes import chat, suggest, summarize

app = FastAPI(
    title="ODP AI Service",
    version="0.1.0",
)

app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(suggest.router, prefix="/api/v1/suggest", tags=["Suggest"])
app.include_router(summarize.router, prefix="/api/v1/summarize", tags=["Summarize"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-service"}
