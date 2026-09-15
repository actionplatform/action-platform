"""Accounts, browser sessions, organizations, the device flow and scoped API tokens, on one database session."""

from app.services.auth.accounts import Accounts
from app.services.auth.base import (
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
from app.services.auth.device import Device
from app.services.auth.organizations import Organizations
from app.services.auth.sessions import Sessions
from app.services.auth.tokens import Tokens


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
