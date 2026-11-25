"""Bitbucket Cloud: git-flow as branch restrictions and merge checks, the platform's account the only exception to the push restriction."""

from __future__ import annotations

import base64
from typing import Any, Optional

from action_platform.abc.branch_protection import BranchProtection
from action_platform.core.flow.protection import (
    CHECK,
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

OAUTH_USERNAME = "x-token-auth"
KINDS = (
    "push",
    "force",
    "delete",
    "require_passing_builds_to_merge",
    "enforce_merge_checks",
)
MERGE_CHECKS = (
    "Bitbucket counts passing builds and cannot require a check by name; it blocks "
    "the merge only on the Premium plan (enforced merge checks), which the platform "
    "cannot read"
)


class BitbucketProtection(BranchProtection):
    kind = "bitbucket"

    def __init__(
        self,
        repo: str,
        token: str,
        username: Optional[str] = None,
        send: Optional[Send] = None,
    ) -> None:
        self.repo = repo
        self.send = send or sender(
            "https://api.bitbucket.org/2.0", _headers(token, username)
        )
        self._me: Optional[Identity] = None

    def identity(self) -> Optional[Identity]:
        if self._me is None:
            try:
                me = self.send("GET", "/user", None) or {}
            except HostRefused:
                return None

            if not me.get("uuid"):
                return None

            self._me = Identity(
                "user",
                me["uuid"],
                me.get("display_name") or me.get("nickname") or me["uuid"],
            )

        return self._me

    @staticmethod
    def builds(policy: Policy) -> int:
        return max(1, len(policy.checks))

    def wanted(self, policy: Policy, branch: str) -> dict[str, dict[str, Any]]:
        me = self.identity()
        base = {"branch_match_kind": "glob", "pattern": branch}

        return {
            "push": {
                **base,
                "kind": "push",
                "users": [{"uuid": me.id}] if me else [],
                "groups": [],
            },
            "force": {**base, "kind": "force"},
            "delete": {**base, "kind": "delete"},
            "require_passing_builds_to_merge": {
                **base,
                "kind": "require_passing_builds_to_merge",
                "value": self.builds(policy),
            },
            "enforce_merge_checks": {**base, "kind": "enforce_merge_checks"},
        }

    def _restrictions(self) -> dict[tuple[str, str], dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page: Optional[str] = (
            f"/repositories/{self.repo}/branch-restrictions?pagelen=100"
        )

        while page:
            data = self.send("GET", page, None) or {}
            rows.extend(data.get("values") or [])
            page = data.get("next")

        return {
            (r.get("kind"), r.get("pattern")): r
            for r in rows
            if r.get("kind") in KINDS and r.get("branch_match_kind", "glob") == "glob"
        }

    @staticmethod
    def _differs(row: dict[str, Any], want: dict[str, Any]) -> bool:
        if want["kind"] == "push":
            users = {u.get("uuid") for u in row.get("users") or []}
            wanted = {u["uuid"] for u in want["users"]}

            return users != wanted or bool(row.get("groups"))

        if want["kind"] == "require_passing_builds_to_merge":
            return (row.get("value") or 0) < want["value"]

        return False

    def status(self, policy: Policy) -> ProtectionState:
        me = self.identity()
        state = ProtectionState(
            "bitbucket", policy.branches, policy.checks, bypass=me.name if me else None
        )

        if not policy.branches:
            return state.refuse("the repository has none of main, master or develop")

        if me is None:
            return state.refuse(
                "cannot read the account the platform pushes with (GET /user); a workspace or repository access token has none — connect Bitbucket with an account"
            )

        try:
            rows = self._restrictions()
        except HostRefused as e:
            return state.refuse(refusal(e))

        problems: dict[str, list[str]] = {k: [] for k in KINDS}

        for b in policy.branches:
            for kind, want in self.wanted(policy, b).items():
                row = rows.get((kind, b))

                if row is None:
                    problems[kind].append(b)
                    state.drift.append(f"{b}: `{kind}` restriction missing")
                elif self._differs(row, want):
                    problems[kind].append(b)
                    state.drift.append(
                        f"{b}: `{kind}` restriction differs from the policy"
                    )

        def native(rules: tuple[str, ...], kind: str, detail: str) -> None:
            for rule in rules:
                if problems[kind]:
                    state.set(
                        rule,
                        INACTIVE,
                        f"`{kind}` restriction missing or different on "
                        + ", ".join(problems[kind]),
                    )
                else:
                    state.set(rule, NATIVE, detail)

        native(
            (DIRECT_PUSH, PULL_REQUEST),
            "push",
            f"only {me.name} pushes; everyone else merges through a pull request",
        )
        native((FORCE_PUSH,), "force", "blocked by a branch restriction")
        native((DELETION,), "delete", "blocked by a branch restriction")

        if not policy.checks:
            state.set(
                REQUIRED_CHECKS,
                INACTIVE,
                "the repository's CI runs no `gitflow` or `conventional-commit` step",
            )
        elif (
            problems["require_passing_builds_to_merge"]
            or problems["enforce_merge_checks"]
        ):
            state.set(REQUIRED_CHECKS, INACTIVE, "merge checks missing or different")
        else:
            state.set(
                REQUIRED_CHECKS,
                CHECK,
                f"{self.builds(policy)} passing build(s) required; {MERGE_CHECKS}",
            )

        check_rules(state, policy, False)

        return state

    def apply(self, policy: Policy) -> ProtectionState:
        me = self.identity()

        if me is None or not policy.branches:
            return self.status(policy)

        try:
            rows = self._restrictions()

            for b in policy.branches:
                for kind, want in self.wanted(policy, b).items():
                    row = rows.get((kind, b))

                    if row is None:
                        self.send(
                            "POST",
                            f"/repositories/{self.repo}/branch-restrictions",
                            want,
                        )
                    elif self._differs(row, want):
                        self.send(
                            "PUT",
                            f"/repositories/{self.repo}/branch-restrictions/{row['id']}",
                            want,
                        )
        except HostRefused as e:
            return ProtectionState("bitbucket", policy.branches, policy.checks).refuse(
                refusal(e)
            )

        return self.status(policy)


def _headers(token: str, username: Optional[str]) -> dict[str, str]:
    if username and username != OAUTH_USERNAME:
        raw = base64.b64encode(f"{username}:{token}".encode()).decode()

        return {"authorization": f"Basic {raw}"}

    return {"authorization": f"Bearer {token}"}


def refusal(e: HostRefused) -> str:
    detail = e.detail or str(e)

    if e.status == 403:
        return f"Bitbucket refused ({e.status}): {detail} — the platform's account needs admin on the repository"

    return f"Bitbucket answered {e.status or 'an error'}: {detail}"


__all__ = ["BitbucketProtection", "MERGE_CHECKS", "refusal"]
