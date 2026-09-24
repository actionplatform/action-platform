"""Who is calling a request and what it may reach: `Caller` resolved against the directory, `Authorizer` (rule ∩ scope ∩ reach), `JobDispatcher` (jobs), `Planner` (one /api/v1 call decided) — ruled by core.access."""

from app.services.access.caller import Caller, resolve_caller
from app.services.access.enrich import credentials_for, enrich

__all__ = ["Caller", "credentials_for", "enrich", "resolve_caller"]
