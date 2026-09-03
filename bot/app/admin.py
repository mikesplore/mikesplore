import httpx

from .config import settings


async def create_entry(entry: dict) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.post("/entries", json=entry, headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()
        return response.json()
