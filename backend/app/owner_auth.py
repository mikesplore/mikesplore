"""Short-lived owner sessions for browser-based portfolio curation."""

from datetime import datetime, timedelta, timezone
import secrets
from threading import Lock

from fastapi import Header, HTTPException, status

from .config import settings

_sessions: dict[str, datetime] = {}
_failed_attempts: dict[str, tuple[int, datetime]] = {}
_lock = Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def verify_pin(pin: str, client_key: str) -> str:
    if not settings.owner_pin:
        raise HTTPException(status_code=503, detail="Owner mode is not configured")
    now = _now()
    with _lock:
        attempts, until = _failed_attempts.get(client_key, (0, now))
        if until > now:
            raise HTTPException(status_code=429, detail="Too many PIN attempts; try again later")
        if not secrets.compare_digest(pin, settings.owner_pin):
            attempts += 1
            if attempts >= settings.owner_max_attempts:
                _failed_attempts[client_key] = (0, now + timedelta(minutes=5))
                raise HTTPException(status_code=429, detail="Too many PIN attempts; try again later")
            _failed_attempts[client_key] = (attempts, now)
            raise HTTPException(status_code=401, detail="Invalid owner PIN")
        _failed_attempts.pop(client_key, None)
        token = secrets.token_urlsafe(32)
        _sessions[token] = now + timedelta(minutes=settings.owner_session_minutes)
        return token


def require_owner_session(authorization: str | None = Header(default=None)) -> None:
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not is_owner_session(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Owner session required")


def is_owner_session(token: str) -> bool:
    with _lock:
        expires = _sessions.get(token)
        if not expires:
            return False
        if expires <= _now():
            _sessions.pop(token, None)
            return False
        return True


def lock_owner_session(authorization: str | None) -> None:
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    with _lock:
        _sessions.pop(token, None)
