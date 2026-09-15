"""Identity tokens the platform signs."""

from typing import Optional

from pydantic import BaseModel


class IdentityTokenRequest(BaseModel):
    audience: str
    project_id: Optional[str] = None
    app_id: Optional[str] = None


class IdentityToken(BaseModel):
    token: str
    subject: str
    audience: str
    expires_in: int
    issuer: str
