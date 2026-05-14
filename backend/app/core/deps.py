"""FastAPI dependency providers.

Re-exports get_db and adds a `get_current_user` dependency that reads
request.state.user populated by AuthMiddleware.
"""
from fastapi import Request
from app.core.exceptions import AuthenticationError
from app.database import get_db  # noqa: re-export


def get_current_user(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not user:
        raise AuthenticationError("尚未登入")
    return user


def get_optional_user(request: Request) -> dict | None:
    return getattr(request.state, "user", None)


__all__ = ["get_db", "get_current_user", "get_optional_user"]
