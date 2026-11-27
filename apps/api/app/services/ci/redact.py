"""Known secret shapes masked out of CI output before it leaves the platform."""

import re

MASK = "****"

PATTERNS = [
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
    ),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
]

LABELLED = re.compile(
    r"(?i)(\b(?:authorization|proxy-authorization)\s*[:=]\s*(?:bearer|basic|token)?\s*)([^\s'\"]{8,})"
)


def redact(text: str) -> str:
    for pattern in PATTERNS:
        text = pattern.sub(MASK, text)

    return LABELLED.sub(lambda m: m.group(1) + MASK, text)
