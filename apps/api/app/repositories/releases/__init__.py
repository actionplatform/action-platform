"""Releases: the platform's rows, one per tag of an app."""

from app.repositories.releases.store import ReleaseStore, split_tag, tag_of

__all__ = ["ReleaseStore", "split_tag", "tag_of"]
