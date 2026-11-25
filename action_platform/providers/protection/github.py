"""GitHub: git-flow as repository rulesets, the platform's GitHub App the only bypass actor."""

from __future__ import annotations

import urllib.parse
from typing import Any, Optional

from action_platform.abc.branch_protection import BranchProtection
from action_platform.core.flow.protection import (
    DELETION,
    DIRECT_PUSH,
    FORCE_PUSH,
    INACTIVE,
    NATIVE,
    PULL_REQUEST,
    REQUIRED_CHECKS,
    Identity,
    Policy,
    ProtectionState,
    check_rules,
)
from action_platform.providers.protection.http import HostRefused, Send, sender

RULESET = "action-platform git-flow"
NAMES_RULESET = "action-platform git-flow names"
PULL_REQUEST_PARAMETERS = {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews_on_push": False,
    "require_code_owner_review": False,
    "require_last_push_approval": False,
    "required_review_thread_resolution": False,
}


class GithubProtection(BranchProtection):
    kind = "github"

    def __init__(
        self,
        repo: str,
        token: str,
        base_url: Optional[str] = None,
        app: Optional[Identity] = None,
        send: Optional[Send] = None,
    ) -> None:
        self.repo = repo
        self.app = app
        self.send = send or sender(
            (base_url or "https://api.github.com").rstrip("/"),
            {
                "authorization": f"Bearer {token}",
                "accept": "application/vnd.github+json",
                "x-github-api-version": "2022-11-28",
            },
        )

    def identity(self) -> Optional[Identity]:
        return self.app

    def ruleset(self, policy: Policy) -> dict[str, Any]:
        rules: list[dict[str, Any]] = [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "pull_request", "parameters": dict(PULL_REQUEST_PARAMETERS)},
        ]

        if policy.checks:
            rules.append(
                {
                    "type": "required_status_checks",
                    "parameters": {
                        "strict_required_status_checks_policy": False,
                        "required_status_checks": [
                            {"context": c} for c in policy.checks
                        ],
                    },
                }
            )

        return {
            "name": RULESET,
            "target": "branch",
            "enforcement": "active",
            "bypass_actors": self._bypass(policy),
            "conditions": {
                "ref_name": {
                    "include": [f"refs/heads/{b}" for b in policy.branches],
                    "exclude": [],
                }
            },
            "rules": rules,
        }

    def names_ruleset(self, policy: Policy) -> dict[str, Any]:
        return {
            "name": NAMES_RULESET,
            "target": "branch",
            "enforcement": "active",
            "bypass_actors": self._bypass(policy),
            "conditions": {"ref_name": {"include": ["~ALL"], "exclude": []}},
            "rules": [
                {
                    "type": "branch_name_pattern",
                    "parameters": {
                        "name": "git-flow branch name",
                        "negate": False,
                        "operator": "regex",
                        "pattern": policy.branch_pattern,
                    },
                },
                {
                    "type": "commit_message_pattern",
                    "parameters": {
                        "name": "Conventional Commits",
                        "negate": False,
                        "operator": "regex",
                        "pattern": policy.commit_pattern,
                    },
                },
            ],
        }

    @staticmethod
    def _bypass(policy: Policy) -> list[dict[str, Any]]:
        if policy.identity is None:
            return []

        return [
            {
                "actor_id": int(policy.identity.id),
                "actor_type": "Integration",
                "bypass_mode": "always",
            }
        ]

    def _state(self, policy: Policy) -> ProtectionState:
        return ProtectionState(
            "github",
            policy.branches,
            policy.checks,
            bypass=f"GitHub App {policy.identity.name}" if policy.identity else None,
        )

    def _find(self, name: str) -> Optional[dict[str, Any]]:
        listing = self.send(
            "GET", f"/repos/{self.repo}/rulesets?includes_parents=false", None
        )

        found = next(
            (
                r
                for r in listing or []
                if r.get("name") == name
                and r.get("source_type", "Repository") == "Repository"
            ),
            None,
        )

        if found is None:
            return None

        return self.send("GET", f"/repos/{self.repo}/rulesets/{found['id']}", None)

    def enterprise(self) -> bool:
        """Whether the repository's owner is an organization on GitHub Enterprise, the only plan with commit metadata rules."""
        try:
            repo = self.send("GET", f"/repos/{self.repo}", None) or {}
            owner = repo.get("owner") or {}

            if owner.get("type") != "Organization":
                return False

            org = (
                self.send("GET", f"/orgs/{urllib.parse.quote(owner['login'])}", None)
                or {}
            )
        except HostRefused:
            return False

        return ((org.get("plan") or {}).get("name") or "").lower() == "enterprise"

    def status(self, policy: Policy) -> ProtectionState:
        state = self._state(policy)

        if not policy.branches:
            return state.refuse("the repository has none of main, master or develop")

        try:
            current = self._find(RULESET)
            names = self._find(NAMES_RULESET)
        except HostRefused as e:
            return state.refuse(refusal(e))

        if current is None:
            state.refuse(f"no `{RULESET}` ruleset on the repository")
            state.error = None
            state.drift.append(f"ruleset `{RULESET}` missing")

            return state

        self._read(state, current, policy)
        native_names = names is not None and self._names_match(names, policy)

        if names is not None and not native_names:
            state.drift.append(f"ruleset `{NAMES_RULESET}` differs from the policy")

        check_rules(state, policy, native_names)

        if state.drift:
            state.changed_by = self._changed_by(current)

        return state

    def _read(
        self, state: ProtectionState, current: dict[str, Any], policy: Policy
    ) -> None:
        by_type = {r.get("type"): r for r in current.get("rules") or []}
        include = set(
            ((current.get("conditions") or {}).get("ref_name") or {}).get("include")
            or []
        )
        wanted = {f"refs/heads/{b}" for b in policy.branches}
        active = current.get("enforcement") == "active"
        actors = {
            (a.get("actor_type"), str(a.get("actor_id")))
            for a in current.get("bypass_actors") or []
        }
        expected = {("Integration", policy.identity.id)} if policy.identity else set()

        if not active:
            state.drift.append(f"ruleset enforcement is {current.get('enforcement')}")

        if not wanted <= include:
            state.drift.append(
                "branches not covered: "
                + ", ".join(sorted(b[11:] for b in wanted - include))
            )

        if actors - expected:
            state.drift.append(
                "bypass granted to "
                + ", ".join(f"{t} {i}" for t, i in sorted(actors - expected, key=str))
            )

        if expected - actors:
            state.drift.append("the platform's GitHub App is not a bypass actor")

        def native(rule: str, kind: str, detail: str) -> None:
            if active and kind in by_type and wanted <= include:
                state.set(rule, NATIVE, detail)
            else:
                state.set(rule, INACTIVE, f"the ruleset has no active `{kind}` rule")

                if kind not in by_type:
                    state.drift.append(f"rule `{kind}` missing")

        native(
            DIRECT_PUSH,
            "pull_request",
            "changes reach the branch only through a pull request",
        )
        native(PULL_REQUEST, "pull_request", "required by the ruleset")
        native(FORCE_PUSH, "non_fast_forward", "blocked by the ruleset")
        native(DELETION, "deletion", "blocked by the ruleset")

        if not policy.checks:
            state.set(
                REQUIRED_CHECKS,
                INACTIVE,
                "the repository's CI reports no check the platform can require",
            )

            return

        checks = by_type.get("required_status_checks") or {}
        required = {
            c.get("context")
            for c in (checks.get("parameters") or {}).get("required_status_checks")
            or []
        }
        missing = [c for c in policy.checks if c not in required]

        if active and not missing:
            state.set(REQUIRED_CHECKS, NATIVE, "required: " + ", ".join(policy.checks))
        else:
            state.set(
                REQUIRED_CHECKS,
                INACTIVE,
                "not required: " + ", ".join(missing or policy.checks),
            )
            state.drift.append(
                "required checks missing: " + ", ".join(missing or policy.checks)
            )

    def _names_match(self, names: dict[str, Any], policy: Policy) -> bool:
        patterns = {
            r.get("type"): (r.get("parameters") or {}).get("pattern")
            for r in names.get("rules") or []
        }

        return names.get("enforcement") == "active" and patterns == {
            "branch_name_pattern": policy.branch_pattern,
            "commit_message_pattern": policy.commit_pattern,
        }

    def _changed_by(self, current: dict[str, Any]) -> Optional[str]:
        try:
            history = self.send(
                "GET",
                f"/repos/{self.repo}/rulesets/{current['id']}/history?per_page=1",
                None,
            )
        except HostRefused:
            return None

        actor = ((history or [{}])[0] or {}).get("actor") or {}

        if not actor:
            return None

        return f"{actor.get('type', 'actor')} {actor.get('id')}".strip()

    def apply(self, policy: Policy) -> ProtectionState:
        state = self._state(policy)

        if policy.identity is None:
            return state.refuse(
                "the platform has no GitHub App identity to exempt; nothing was applied"
            )

        if not policy.branches:
            return state.refuse("the repository has none of main, master or develop")

        try:
            self._put(RULESET, self.ruleset(policy))
        except HostRefused as e:
            return state.refuse(refusal(e))

        if self.enterprise():
            try:
                self._put(NAMES_RULESET, self.names_ruleset(policy))
            except HostRefused:
                pass

        return self.status(policy)

    def _put(self, name: str, body: dict[str, Any]) -> None:
        current = self._find(name)

        if current is None:
            self.send("POST", f"/repos/{self.repo}/rulesets", body)
        else:
            self.send("PUT", f"/repos/{self.repo}/rulesets/{current['id']}", body)

    def contexts(self, origin: str) -> tuple[str, ...]:
        try:
            pulls = self.send(
                "GET", f"/repos/{self.repo}/pulls?state=closed&per_page=20", None
            )
        except HostRefused:
            return ()

        heads = [
            p["head"]["sha"]
            for p in pulls or []
            if p.get("merged_at") and (p.get("head") or {}).get("sha")
        ][:5]
        found: set[str] = set()

        for sha in heads:
            try:
                status = self.send(
                    "GET", f"/repos/{self.repo}/commits/{sha}/status", None
                )
            except HostRefused:
                continue

            for s in (status or {}).get("statuses") or []:
                if (s.get("target_url") or "").startswith(
                    origin.rstrip("/") + "/"
                ) and s.get("context"):
                    found.add(s["context"])

        return tuple(sorted(found))


def refusal(e: HostRefused) -> str:
    detail = e.detail or str(e)

    if e.status in (403, 404):
        return f"GitHub refused rulesets on this repository ({e.status}): {detail}"

    return f"GitHub answered {e.status or 'an error'}: {detail}"


__all__ = ["GithubProtection", "NAMES_RULESET", "RULESET", "refusal"]
