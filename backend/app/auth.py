from fastapi import Header, HTTPException, status

from .config import settings
from .owner_auth import require_owner_session


def require_service_key(
    x_service_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    if settings.service_api_key and x_service_api_key == settings.service_api_key:
        return
    try:
        require_owner_session(authorization)
        return
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Service key or owner session required")
