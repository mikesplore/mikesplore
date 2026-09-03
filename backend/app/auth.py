from fastapi import Header, HTTPException, status

from .config import settings


def require_service_key(x_service_api_key: str | None = Header(default=None)) -> None:
    if not settings.service_api_key or x_service_api_key != settings.service_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service API key")
