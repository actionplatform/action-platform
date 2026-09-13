"""TemplateStore ABC: where template repositories come from."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class TemplateStoreABC(ABC):
    @abstractmethod
    def checkout(self, source: Any, update: bool = False) -> Path: ...

    @abstractmethod
    def official(self, update: bool = False) -> Path: ...
