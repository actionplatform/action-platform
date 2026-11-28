"""What a remote holds, asked without a clone: `git ls-remote` of its branches, tags and default branch."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from action_platform.core.flow.repo.runner import GitRunner, subprocess_git
from action_platform.core.flow.repo.sync import SyncError, _fetch_problem

HEADS = "refs/heads/"
TAGS = "refs/tags/"
PEELED = "^{}"


@dataclass
class RemoteRefs:
    """Branch and tag names with the commit each points at; an annotated tag is peeled to its commit."""

    branches: dict[str, str] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
    default_branch: str | None = None

    @property
    def digest(self) -> str:
        """One hash of every ref: equal digests mean nothing moved."""
        lines = [f"h {n} {s}" for n, s in sorted(self.branches.items())]
        lines += [f"t {n} {s}" for n, s in sorted(self.tags.items())]
        lines.append(f"d {self.default_branch or ''}")

        return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def remote_refs(url: str, runner: GitRunner = subprocess_git) -> RemoteRefs:
    args = ["ls-remote", "--symref", url]
    result = runner(args)

    if result.returncode != 0:
        raise SyncError(_fetch_problem(result.stderr or ""))

    return parse(result.stdout)


def parse(out: str) -> RemoteRefs:
    refs = RemoteRefs()
    tags: dict[str, str] = {}
    peeled: dict[str, str] = {}

    for line in out.splitlines():
        if not line.strip():
            continue

        left, _, name = line.partition("\t")

        if left.startswith("ref: "):
            if name == "HEAD" and left[5:].startswith(HEADS):
                refs.default_branch = left[5:].removeprefix(HEADS)

            continue

        if name.startswith(HEADS):
            refs.branches[name.removeprefix(HEADS)] = left
        elif name.startswith(TAGS) and name.endswith(PEELED):
            peeled[name.removeprefix(TAGS).removesuffix(PEELED)] = left
        elif name.startswith(TAGS):
            tags[name.removeprefix(TAGS)] = left

    refs.tags = {name: peeled.get(name, sha) for name, sha in tags.items()}

    return refs
