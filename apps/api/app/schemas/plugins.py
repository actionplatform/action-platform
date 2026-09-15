"""Plugins on the hosted platform: what a job answers, what a plugin remembers."""

from typing import Any

from pydantic import BaseModel


class PluginQueued(BaseModel):
    job: str
    poll: str


class PluginOptions(BaseModel):
    options: dict[str, Any]
