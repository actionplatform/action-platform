"""action_platform.core.scaffold.templates — the matrix read from index.json, and repositories as sources."""

from __future__ import annotations

import json

from action_platform.core.exception import TemplateError
from action_platform.core.scaffold.templates import (
    Matrix,
    TemplateSource,
    detect_language,
    plain_matrix,
)
from tests.support import TempCase

INDEX = json.dumps(
    {
        "types": [{"id": "web", "label": "Web application", "description": "APIs"}],
        "stacks": [
            {"id": "python", "label": "Python", "icon": "assets/icons/python.svg"}
        ],
        "projects": [
            {
                "id": "web/python/fastapi",
                "default": True,
                "description": "FastAPI",
                "framework": "FastAPI",
                "icons": {
                    "language": "assets/icons/python.svg",
                    "framework": "assets/icons/fastapi.svg",
                },
            },
            {"id": "web/python/django", "description": "Django"},
            {"id": "web/go/gin", "default": True},
            {"id": "empty", "type": "empty", "description": "Only platform.toml"},
        ],
        "clouds": [
            {
                "id": "aws/lambda",
                "description": "SAM",
                "languages": ["python"],
                "types": ["web"],
            },
            {"id": "docker", "description": "Dockerfile"},
        ],
    }
)


class MatrixTest(TempCase):
    def setUp(self):
        super().setUp()
        path = self.tmp_path / "index.json"
        path.write_text(INDEX)
        self.matrix = Matrix.from_json(path)

    def test_types_and_stacks(self):
        self.assertEqual(self.matrix.types(), ["empty", "web"])
        self.assertEqual(self.matrix.stacks("web"), ["go", "python"])
        self.assertEqual(self.matrix.stacks("empty"), [])

    def test_resolve_default_explicit_and_empty(self):
        leaf = self.matrix.resolve("web", "python", None)
        self.assertEqual(leaf.template, "fastapi")
        self.assertEqual(leaf.directory, "projects/web/python/fastapi")
        self.assertEqual(
            self.matrix.resolve("web", "python", "django").description, "Django"
        )
        self.assertEqual(
            self.matrix.resolve("empty", None, None).directory, "projects/empty"
        )

    def test_resolve_errors(self):
        for args in [
            ("nope", None, None),
            ("web", None, None),
            ("web", "rust", None),
            ("web", "python", "flask"),
        ]:
            with self.assertRaises(TemplateError):
                self.matrix.resolve(*args)

    def test_clouds(self):
        self.assertEqual([c.name for c in self.matrix.clouds], ["aws/lambda", "docker"])
        lam = self.matrix.cloud("aws/lambda")
        self.assertEqual(lam.directory, "cloud/aws/lambda")
        self.assertTrue(lam.supports("web", "python"))
        self.assertFalse(lam.supports("web", "go"))
        self.assertFalse(lam.supports("library", "python"))
        self.assertTrue(self.matrix.cloud("docker").supports("library", "rust"))
        self.assertEqual(
            [c.name for c in self.matrix.clouds_for("web", "go")], ["docker"]
        )
        with self.assertRaises(TemplateError):
            self.matrix.cloud("gcp/run")

    def test_empty_sections(self):
        path = self.tmp_path / "empty.json"
        path.write_text('{"projects": [], "clouds": []}')
        matrix = Matrix.from_json(path)
        self.assertEqual(matrix.leaves, [])
        self.assertEqual(matrix.clouds, [])

    def test_services(self):
        data = json.loads(INDEX)
        data["services"] = [
            {"id": "postgres", "description": "db", "providers": ["docker", "aws-rds"]}
        ]
        path = self.tmp_path / "svc.json"
        path.write_text(json.dumps(data))
        matrix = Matrix.from_json(path)
        svc = matrix.service("postgres")
        self.assertEqual(svc.directory, "service/postgres")
        self.assertEqual(svc.providers, ["docker", "aws-rds"])
        with self.assertRaises(TemplateError):
            matrix.service("kafka")


class PlainRepositoryTest(TempCase):
    def test_source_parsing(self):
        self.assertEqual(TemplateSource.parse("https://x/y.git@main").ref, "main")
        self.assertEqual(TemplateSource.parse("https://x/y.git").ref, "main")
        self.assertEqual(
            TemplateSource.parse("https://x/y.git", name="acme").label, "acme"
        )
        self.assertEqual(TemplateSource.parse("https://x/y.git").label, "y")

    def test_language_detection_by_marker_then_by_extension(self):
        (self.tmp_path / "go.mod").write_text("module x\n")
        self.assertEqual(detect_language(self.tmp_path), "go")

        src = self.tmp_path / "src"
        src.mkdir()
        (self.tmp_path / "go.mod").unlink()
        for name in ["a.ts", "b.ts", "c.py"]:
            (src / name).write_text("")
        self.assertEqual(detect_language(self.tmp_path), "node")

        (self.tmp_path / "README.md").write_text("only docs")
        for name in ["a.ts", "b.ts", "c.py"]:
            (src / name).unlink()
        self.assertEqual(detect_language(self.tmp_path), "")

    def test_plain_repository_is_one_template_that_resolves_under_any_type(self):
        (self.tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        matrix = plain_matrix(
            TemplateSource("https://x/starter.git", "main", "starter"), self.tmp_path
        )

        (leaf,) = matrix.leaves
        self.assertTrue(leaf.plain)
        self.assertEqual(
            (leaf.template, leaf.stack, leaf.directory), ("starter", "python", "")
        )
        self.assertEqual(matrix.resolve("web", None, "starter").type, "web")
        self.assertEqual(matrix.resolve("library", "python", "starter").type, "library")
