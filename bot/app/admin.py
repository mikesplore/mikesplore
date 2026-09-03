import httpx

from .config import settings


async def create_entry(entry: dict) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.post("/entries", json=entry, headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()
        return response.json()


async def upload_certificate(title: str, filename: str, content: bytes, content_type: str | None) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=30) as client:
        response = await client.post("/certificates", data={"title": title}, files={"file": (filename, content, content_type or "application/octet-stream")}, headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()
        return response.json()


async def upload_asset(asset_type: str, label: str, filename: str, content: bytes, content_type: str | None) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=30) as client:
        response = await client.post("/assets", data={"asset_type": asset_type, "label": label}, files={"file": (filename, content, content_type or "application/octet-stream")}, headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()
        return response.json()
