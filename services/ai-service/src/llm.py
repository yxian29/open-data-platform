import httpx
from src.config import settings


async def chat(prompt: str) -> str:
    """Send a prompt to the claude CLI bridge and return the response text."""
    async with httpx.AsyncClient() as client:
        r = await client.post(
            settings.claude_bridge_url,
            json={"prompt": prompt},
            timeout=120.0,
        )
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"Bridge error: {data['error']}")
        return data["content"]
