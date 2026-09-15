"""An app's disposable clone and everything done inside it: manifest, configuration, git-flow, state, releases."""

from app.services.workspace.checkout import CLONES, Clones, Workspaces

__all__ = ["CLONES", "Clones", "Workspaces"]
