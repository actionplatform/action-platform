"""The permission rules per route: which permission each /api/v1 path needs and what the gate does around it."""

from app.core.access.rules import DIRECTORY, RULES, WORKSPACE_ROOTS, Rule, rule_for

__all__ = ["DIRECTORY", "RULES", "WORKSPACE_ROOTS", "Rule", "rule_for"]
