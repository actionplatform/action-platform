"""The snapshot the app pages read, built from the code host instead of a clone: refs from `git ls-remote`, commits, files and tags from the host's API, the pending drafts laid over the files."""

from __future__ import annotations

import fnmatch
from dataclasses import asdict
from typing import Optional

from action_platform.abc.source_host import ReadsRepository
from action_platform.core.context import CommitRow, TagRow
from action_platform.core.files import CONFIG_FILE, LAST_VERSION_FILE
from action_platform.core.flow import gitflow
from action_platform.core.flow.remote import RemoteRefs
from action_platform.core.flow.remote_audit import audit
from action_platform.core.manifest.manifest import dump_toml
from action_platform.core.release.release import STABLE_BRANCHES
from app.repositories.configuration.config_store import ConfigStore
from app.repositories.workspace.registry import Registry
from app.repositories.workspace.snapshots import SnapshotStore
from app.services.workspace.facts import same_toml
from app.services.workspace.manifest import describe
from app.services.workspace.snapshot import COMMITS

VERSION_TAG = "v[0-9]*"


class RemoteSnapshot:
    def __init__(
        self,
        registry: Registry,
        reader: ReadsRepository,
        repo: str,
        configs: ConfigStore | None = None,
    ) -> None:
        self.registry = registry
        self.reader = reader
        self.repo = repo
        self.configs = configs or ConfigStore(registry.store.database)
        self.store = SnapshotStore(registry.store.database)

    def take(self, id: str, refs: RemoteRefs) -> dict:
        entry = self.registry.get(id)
        branch = entry.checked_out or refs.default_branch or entry.default_branch
        drafts = self.registry.drafts.files(id)

        def read(path: str) -> Optional[str]:
            if path in drafts:
                return drafts[path]

            return self.reader.file(self.repo, branch, path)

        toml = read(CONFIG_FILE)
        self.configs.adopt_text(id, toml)
        config = self.configs.resolve_text(id, toml)
        tags = self.reader.tags(self.repo)
        tagged = any(fnmatch.fnmatch(t.name, VERSION_TAG) for t in tags)

        def last_version(path: str) -> Optional[str]:
            text = read(
                f"{path.strip('/')}/{LAST_VERSION_FILE}" if path else LAST_VERSION_FILE
            )

            if text is None:
                return None

            return text.strip() if tagged else "0.0.0"

        detail = describe(config, last_version)
        detail.update(
            id=id,
            url=entry.url,
            default_branch=entry.default_branch,
            branch=branch,
            latest_tag=tags[0].name if tags else None,
            clean=not drafts,
        )
        report = audit(self.reader, self.repo, branch, refs, tags)
        content = dump_toml(config)
        data = {
            "detail": detail,
            "gitflow": {**asdict(report), "ok": report.ok},
            "commits": [
                _commit(c) for c in self.reader.commits(self.repo, branch, COMMITS)
            ],
            "branches": [_branch(name, sha) for name, sha in refs.branches.items()],
            "tags": [t.name for t in tags],
            "releases": [_release(t, i == 0) for i, t in enumerate(tags)],
            "manifest": {
                "content": content,
                "mirrored": toml is not None and same_toml(toml, content),
            },
            "refs_digest": refs.digest,
        }
        self.store.set(id, data)

        return data

    def unchanged(self, id: str, refs: RemoteRefs) -> bool:
        """Whether the snapshot was taken from these very refs, with no draft since."""
        found = self.store.get(id)

        if found is None or self.registry.drafts.paths(id):
            return False

        return found[0].get("refs_digest") == refs.digest


def _commit(c: CommitRow) -> dict:
    return {
        "sha": c.sha[:7],
        "subject": c.subject,
        "author": c.author or "",
        "date": c.date.strftime("%Y-%m-%d") if c.date else "",
    }


def _branch(name: str, sha: str) -> dict:
    return {
        "name": name,
        "date": "",
        "sha": sha[:7],
        "kind": gitflow.kind_of(name),
        "protected": name in gitflow.current().protected,
        "stable": name in STABLE_BRANCHES,
        "problem": gitflow.check_branch(name),
    }


def _release(t: TagRow, latest: bool) -> dict:
    version = t.name.split("/")[-1].removeprefix("v")

    return {
        "tag": t.name,
        "version": version,
        "date": t.date.strftime("%Y-%m-%d") if t.date else "",
        "sha": t.sha[:7],
        "subject": t.subject or "",
        "prerelease": "-" in version,
        "latest": latest,
    }
