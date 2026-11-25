"""GitLab: git-flow as protected branches, "pipelines must succeed" and, on Premium, push rules with the platform's account the only one allowed to push."""

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

NO_ONE = 0
DEVELOPER = 30
MAINTAINER = 40
FREE_PUSHERS = "Maintainers (GitLab Free)"
FREE_PUSH = (
    "GitLab Free cannot let one account push and refuse everyone else: Maintainers "
    "keep push access so the platform can push release commits. GitLab Premium "
    "limits pushes to the platform's account"
)


class GitlabProtection(BranchProtection):
    kind = "gitlab"

    def __init__(
        self,
        repo: str,
        token: str,
        base_url: Optional[str] = None,
        send: Optional[Send] = None,
    ) -> None:
        self.repo = repo
        self.id = urllib.parse.quote(repo, safe="")
        self.send = send or sender(
            f"{(base_url or 'https://gitlab.com').rstrip('/')}/api/v4",
            {"authorization": f"Bearer {token}"},
        )
        self._me: Optional[Identity] = None
        self._premium: Optional[bool] = None

    def identity(self) -> Optional[Identity]:
        if self._me is None:
            try:
                me = self.send("GET", "/user", None) or {}
            except HostRefused:
                return None

            if me.get("id") is None:
                return None

            self._me = Identity(
                "user", str(me["id"]), me.get("username") or str(me["id"])
            )

        return self._me

    def premium(self) -> bool:
        """Whether the project's plan has push rules and per-account push access (Premium and Ultimate): the push rule endpoint answers only there."""
        if self._premium is None:
            try:
                self.send("GET", f"/projects/{self.id}/push_rule", None)
                self._premium = True
            except HostRefused as e:
                if e.status not in (401, 402, 403, 404):
                    raise

                self._premium = False

        return self._premium

    def protected(self, branch: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "name": branch,
            "merge_access_level": DEVELOPER,
            "allow_force_push": False,
        }

        if self.premium() and self.identity() is not None:
            body["push_access_level"] = NO_ONE
            body["allowed_to_push"] = [{"user_id": int(self.identity().id)}]
        else:
            body["push_access_level"] = MAINTAINER

        return body

    def _pushers(self, row: dict[str, Any]) -> set[tuple[str, str]]:
        out: set[tuple[str, str]] = set()

        for level in row.get("push_access_levels") or []:
            if level.get("user_id"):
                out.add(("user", str(level["user_id"])))
            elif level.get("group_id"):
                out.add(("group", str(level["group_id"])))
            elif level.get("deploy_key_id"):
                out.add(("deploy_key", str(level["deploy_key_id"])))
            elif level.get("access_level"):
                out.add(("level", str(level["access_level"])))

        return out

    def _change(self, row: dict[str, Any]) -> dict[str, Any]:
        """The PATCH that leaves only the platform's account in a protected branch's push access, in place."""
        me = self.identity()

        if me is None or self._pushers(row) == {("user", me.id)}:
            return {}

        entries: list[dict[str, Any]] = [
            {"id": level["id"], "_destroy": True}
            for level in row.get("push_access_levels") or []
            if level.get("id") is not None
            and str(level.get("user_id") or "") != me.id
            and (
                level.get("access_level")
                or level.get("user_id")
                or level.get("group_id")
                or level.get("deploy_key_id")
            )
        ]

        if ("user", me.id) not in self._pushers(row):
            entries.append({"user_id": int(me.id)})

        return {"allowed_to_push": entries}

    def _wanted_pushers(self) -> set[tuple[str, str]]:
        me = self.identity()

        if self.premium() and me is not None:
            return {("user", me.id)}

        return {("level", str(MAINTAINER))}

    def _branches(self, policy: Policy) -> dict[str, Optional[dict[str, Any]]]:
        rows: dict[str, Optional[dict[str, Any]]] = {}

        for b in policy.branches:
            try:
                rows[b] = self.send(
                    "GET",
                    f"/projects/{self.id}/protected_branches/{urllib.parse.quote(b, safe='')}",
                    None,
                )
            except HostRefused as e:
                if e.status != 404:
                    raise

                rows[b] = None

        return rows

    def _state(self, policy: Policy) -> ProtectionState:
        me = self.identity()

        return ProtectionState(
            "gitlab",
            policy.branches,
            policy.checks,
            bypass=me.name if me and self.premium() else FREE_PUSHERS,
        )

    def status(self, policy: Policy) -> ProtectionState:
        if not policy.branches:
            return ProtectionState("gitlab").refuse(
                "the repository has none of main, master or develop"
            )

        try:
            state = self._state(policy)
            rows = self._branches(policy)
            project = self.send("GET", f"/projects/{self.id}", None) or {}
            rule = (
                self.send("GET", f"/projects/{self.id}/push_rule", None)
                if self.premium()
                else None
            )
        except HostRefused as e:
            return ProtectionState("gitlab", policy.branches, policy.checks).refuse(
                refusal(e)
            )

        missing = [b for b, row in rows.items() if row is None]
        rows_present = [row for row in rows.values() if row is not None]

        for b in missing:
            state.drift.append(f"{b} is not protected")

        forced = [r["name"] for r in rows_present if r.get("allow_force_push")]

        for b in forced:
            state.drift.append(f"{b} allows force push")

        wanted = self._wanted_pushers()
        loose = (
            [r["name"] for r in rows_present if self._pushers(r) != wanted]
            if self.premium()
            else []
        )

        for b in loose:
            state.drift.append(f"{b}: push access differs from the policy")

        covered = not missing

        state.set(
            FORCE_PUSH,
            NATIVE if covered and not forced else INACTIVE,
            "protected branches refuse force pushes"
            if covered and not forced
            else "force push is allowed on " + ", ".join(missing + forced),
        )
        state.set(
            DELETION,
            NATIVE if covered else INACTIVE,
            "a push cannot delete a protected branch; Maintainers can still delete one from GitLab's UI or API"
            if covered
            else "not protected: " + ", ".join(missing),
        )

        if not self.premium():
            state.set(DIRECT_PUSH, INACTIVE, FREE_PUSH)
            state.set(PULL_REQUEST, INACTIVE, FREE_PUSH)
        elif covered and not loose:
            me = self.identity()
            detail = f"only {me.name if me else 'the platform'} pushes; everyone else merges through a merge request"
            state.set(DIRECT_PUSH, NATIVE, detail)
            state.set(PULL_REQUEST, NATIVE, detail)
        else:
            state.set(DIRECT_PUSH, INACTIVE, "push access differs from the policy")
            state.set(PULL_REQUEST, INACTIVE, "push access differs from the policy")

        succeeds = bool(
            project.get("only_allow_merge_if_pipeline_succeeds")
        ) and not project.get("allow_merge_on_skipped_pipeline")

        if policy.checks and not succeeds:
            state.drift.append("pipelines must succeed is off")

        if not policy.checks:
            state.set(
                REQUIRED_CHECKS,
                INACTIVE,
                "the repository's CI runs no `gitflow` or `conventional-commit` job",
            )
        elif succeeds:
            state.set(
                REQUIRED_CHECKS,
                NATIVE,
                "pipelines must succeed; the pipeline runs " + ", ".join(policy.checks),
            )
        else:
            state.set(REQUIRED_CHECKS, INACTIVE, "pipelines must succeed is off")

        native_names = bool(
            rule
            and rule.get("commit_message_regex") == policy.commit_pattern
            and rule.get("branch_name_regex") == policy.branch_pattern
        )

        if self.premium() and not native_names:
            state.drift.append("push rule differs from the policy")

        check_rules(state, policy, native_names)

        return state

    def apply(self, policy: Policy) -> ProtectionState:
        if not policy.branches:
            return ProtectionState("gitlab").refuse(
                "the repository has none of main, master or develop"
            )

        try:
            premium = self.premium()

            if premium and self.identity() is None:
                return ProtectionState("gitlab", policy.branches, policy.checks).refuse(
                    "cannot read the account the platform pushes with (GET /user); nothing was applied"
                )

            for b, row in self._branches(policy).items():
                if row is None:
                    self.send(
                        "POST",
                        f"/projects/{self.id}/protected_branches",
                        self.protected(b),
                    )
                    continue

                change = self._change(row) if premium else {}

                if row.get("allow_force_push"):
                    change["allow_force_push"] = False

                if change:
                    self.send(
                        "PATCH",
                        f"/projects/{self.id}/protected_branches/{urllib.parse.quote(b, safe='')}",
                        change,
                    )

            if policy.checks:
                self.send(
                    "PUT",
                    f"/projects/{self.id}",
                    {
                        "only_allow_merge_if_pipeline_succeeds": True,
                        "allow_merge_on_skipped_pipeline": False,
                    },
                )

            if premium:
                current = self.send("GET", f"/projects/{self.id}/push_rule", None)
                body = {
                    "commit_message_regex": policy.commit_pattern,
                    "branch_name_regex": policy.branch_pattern,
                }
                self.send(
                    "PUT" if current else "POST", f"/projects/{self.id}/push_rule", body
                )
        except HostRefused as e:
            return ProtectionState("gitlab", policy.branches, policy.checks).refuse(
                refusal(e)
            )

        return self.status(policy)


def refusal(e: HostRefused) -> str:
    detail = e.detail or str(e)

    if e.status == 403:
        return f"GitLab refused ({e.status}): {detail} — the platform's account needs the Maintainer role on the project"

    return f"GitLab answered {e.status or 'an error'}: {detail}"


__all__ = ["FREE_PUSH", "FREE_PUSHERS", "GitlabProtection", "refusal"]
