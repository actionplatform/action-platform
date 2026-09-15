"""Identifiers and slugs."""

import re
import uuid


def new_id() -> str:
    return str(uuid.uuid4())


def slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.strip().lower())).strip(
        "-"
    )
