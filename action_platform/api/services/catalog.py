from action_platform import __version__
from action_platform.core.flow import gitflow
from action_platform.core.scaffold.templates import load_matrix


class CatalogService:
    def version(self) -> dict:
        return {"version": __version__}

    def matrix(self) -> dict:
        _, m = load_matrix()

        return {
            "projects": [
                {
                    "type": leaf.type,
                    "stack": leaf.stack,
                    "template": leaf.template,
                    "default": leaf.default,
                    "description": leaf.description,
                }
                for leaf in m.leaves
            ],
            "clouds": [
                {
                    "name": c.name,
                    "types": c.types,
                    "languages": c.languages,
                    "description": c.description,
                }
                for c in m.clouds
            ],
            "services": [
                {"name": s.name, "providers": s.providers, "description": s.description}
                for s in m.services
            ],
        }

    def gitflow_rules(self) -> dict:
        return {
            "kinds": sorted(gitflow.KINDS),
            "protected": sorted(gitflow.PROTECTED),
            "types": sorted(gitflow.TYPES),
        }
