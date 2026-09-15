"""Accounts, browser sessions, organizations, the device flow and scoped API tokens, on one database session."""

from app.core.auth.accounts import Accounts
from app.core.auth.base import (
    ADMIN_TOKEN_TTL,
    AUDIENCE,
    DEVICE_INTERVAL,
    DEVICE_TTL,
    ISSUER,
    PASSWORD_MIN,
    SESSION_REFRESH_AFTER,
    SESSION_TTL,
    TOKEN_TTL,
    Identity,
    new_id,
    now,
)
from app.core.auth.device import Device
from app.core.auth.organizations import Organizations
from app.core.auth.sessions import Sessions
from app.core.auth.tokens import Tokens


class AuthService(Accounts, Sessions, Organizations, Device, Tokens):
    pass


__all__ = [
    "ADMIN_TOKEN_TTL",
    "AUDIENCE",
    "DEVICE_INTERVAL",
    "DEVICE_TTL",
    "ISSUER",
    "PASSWORD_MIN",
    "SESSION_REFRESH_AFTER",
    "SESSION_TTL",
    "TOKEN_TTL",
    "AuthService",
    "Identity",
    "new_id",
    "now",
]
