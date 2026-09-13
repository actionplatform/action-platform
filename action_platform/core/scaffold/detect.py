"""Which language a repository is written in."""

from __future__ import annotations

from pathlib import Path

MARKERS = [
    ("pyproject.toml", "python"),
    ("go.mod", "go"),
    ("package.json", "node"),
    ("composer.json", "php"),
    ("pom.xml", "java"),
    ("Cargo.toml", "rust"),
    ("requirements.txt", "python"),
    ("setup.py", "python"),
    ("Pipfile", "python"),
    ("build.gradle", "java"),
    ("build.gradle.kts", "java"),
    ("tsconfig.json", "node"),
]

EXTENSIONS = {
    ".py": "python",
    ".go": "go",
    ".ts": "node",
    ".tsx": "node",
    ".js": "node",
    ".jsx": "node",
    ".php": "php",
    ".java": "java",
    ".kt": "java",
    ".rs": "rust",
}

SKIP_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".venv",
    "venv",
    "target",
}


class LanguageDetector:
    """By manifest file first (pyproject.toml, go.mod, package.json…), then by the most common source extension."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def by_marker(self) -> str:
        for marker, language in MARKERS:
            if (self.root / marker).exists():
                return language

        return ""

    def by_extension(self) -> str:
        counts: dict[str, int] = {}

        for path in self.root.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue

            language = EXTENSIONS.get(path.suffix)

            if language and path.is_file():
                counts[language] = counts.get(language, 0) + 1

        return max(counts, key=counts.get) if counts else ""

    def detect(self) -> str:
        return self.by_marker() or self.by_extension()


def detect_language(root: Path) -> str:
    return LanguageDetector(root).detect()
