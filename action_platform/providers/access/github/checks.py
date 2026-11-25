"""Read-only checks of an organization's repositories: branch protection of the default branch and the settings of each repository."""

from __future__ import annotations

import urllib.parse
from typing import Any, Optional

from action_platform.core.service_access import AccessError, Http, Response

from action_platform.providers.access.github.models import (
    BranchProtection,
    OrgSettings,
    RepoProtection,
    RepoSettings,
)


class Org:
    def __init__(self, http: Http, org: str) -> None:
        self.http = http
        self.org = org

    def repos(self, only: Optional[str] = None) -> list[dict[str, Any]]:
        if only:
            return [self._ok(f"repos/{self.org}/{only}")]

        return list(
            self.http.pages(f"orgs/{self.org}/repos", {"type": "all", "per_page": 100})
        )

    def branch_protection(self, only: Optional[str] = None) -> BranchProtection:
        return BranchProtection(
            org=self.org, repos=[self._protection(r) for r in self.repos(only)]
        )

    def repo_settings(self, only: Optional[str] = None) -> OrgSettings:
        return OrgSettings(
            org=self.org,
            repos=[
                self._settings(self._ok(f"repos/{self.org}/{r['name']}"))
                for r in self.repos(only)
            ],
        )

    def _ok(self, path: str) -> dict[str, Any]:
        res = self.http.send("GET", path)

        if res.status >= 400:
            raise AccessError(
                f"github: GET /{path} answered {res.status}: {_message(res)}"
            )

        return res.data

    def _protection(self, repo: dict[str, Any]) -> RepoProtection:
        name = repo["name"]
        branch = repo.get("default_branch") or ""
        out = RepoProtection(
            repo=name, default_branch=branch, archived=bool(repo.get("archived"))
        )
        base = f"repos/{self.org}/{name}"
        quoted = urllib.parse.quote(branch, safe="")
        classic = self.http.send("GET", f"{base}/branches/{quoted}/protection")
        rules = self.http.send("GET", f"{base}/rules/branches/{quoted}")
        none = classic.status == 404 and _message(classic) == "Branch not protected"

        for res in (classic, rules):
            if res.status >= 400 and not (res is classic and none):
                out.note = f"{res.status}: {_message(res)}"

                return out

        kinds = [r["type"] for r in rules.data or []]
        reviews = [0]
        checks: set[str] = set()
        force = True

        if not none:
            data = classic.data
            reviews.append(
                (data.get("required_pull_request_reviews") or {}).get(
                    "required_approving_review_count", 0
                )
            )
            status = data.get("required_status_checks") or {}
            checks.update(
                [c["context"] for c in status.get("checks") or []]
                or status.get("contexts")
                or []
            )
            force = bool((data.get("allow_force_pushes") or {}).get("enabled"))

        for rule in rules.data or []:
            params = rule.get("parameters") or {}

            if rule["type"] == "pull_request":
                reviews.append(params.get("required_approving_review_count", 0))
            elif rule["type"] == "required_status_checks":
                checks.update(
                    c["context"] for c in params.get("required_status_checks") or []
                )

        out.protected = not none or bool(kinds)
        out.rule_types = sorted(set(kinds))
        out.required_reviews = max(reviews)
        out.required_status_checks = sorted(checks)
        out.force_pushes_allowed = force and "non_fast_forward" not in kinds

        return out

    def _settings(self, repo: dict[str, Any]) -> RepoSettings:
        name = repo["name"]
        found = repo.get("security_and_analysis")

        def status(key: str) -> Optional[str]:
            return ((found or {}).get(key) or {}).get("status")

        alerts = self.http.send("GET", f"repos/{self.org}/{name}/vulnerability-alerts")

        return RepoSettings(
            repo=name,
            visibility=repo.get("visibility")
            or ("private" if repo["private"] else "public"),
            default_branch=repo.get("default_branch") or "",
            archived=bool(repo.get("archived")),
            delete_branch_on_merge=repo.get("delete_branch_on_merge"),
            allow_auto_merge=repo.get("allow_auto_merge"),
            secret_scanning=status("secret_scanning"),
            secret_scanning_push_protection=status("secret_scanning_push_protection"),
            dependabot_alerts=_enabled(alerts),
            dependabot_security_updates=status("dependabot_security_updates"),
        )


def _enabled(res: Response) -> Optional[bool]:
    if res.status == 204:
        return True

    if res.status == 404 and "disabled" in _message(res):
        return False

    return None


def _message(res: Response) -> str:
    if isinstance(res.data, dict):
        return str(res.data.get("message", ""))[:300]

    return str(res.data or "")[:300]
