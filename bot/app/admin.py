import httpx

from .config import settings


async def preview_sync(source: str) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=30) as client:
        response = await client.get(f"/admin/sync/{source}", headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()
        return response.json()


async def apply_sync(source: str, items: list[dict], selected: list[str]) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=30) as client:
        response = await client.post(f"/admin/sync/{source}", json={"items": items, "selected": selected}, headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()
        return response.json()


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


async def update_entry(entry_id: str, entry: dict) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        path = f"/entries/slug/{entry_id}" if not _is_uuid(entry_id) else f"/entries/{entry_id}"
        response = await client.patch(path, json=entry, headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()
        return response.json()


def _is_uuid(value: str) -> bool:
    import uuid
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


async def delete_entry(entry_id: str) -> None:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        path = f"/entries/slug/{entry_id}" if not _is_uuid(entry_id) else f"/entries/{entry_id}"
        response = await client.delete(path, headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()


async def update_profile(profile: dict) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.patch("/profile", json=profile, headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()
        return response.json()


async def manage_content(resource: str, action: str, payload: dict) -> dict:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.post("/admin/content", params={"resource": resource, "action": action}, json=payload, headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()
        return response.json()


async def search_admin_content(query: str) -> list[dict]:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.get("/admin/search", params={"q": query}, headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()
        return response.json()


async def delete_asset(asset_id: str) -> None:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.delete(f"/assets/{asset_id}", headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()


async def delete_certificate(certificate_id: str) -> None:
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=10) as client:
        response = await client.delete(f"/certificates/{certificate_id}", headers={"X-Service-Api-Key": settings.service_api_key})
        response.raise_for_status()
