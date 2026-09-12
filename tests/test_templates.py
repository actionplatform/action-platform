"""Template matrix tests."""

from pathlib import Path

import pytest

from action_platform.core.exception import TemplateError
from action_platform.core.templates import Matrix

INDEX = """
[project.web.python.fastapi]
default = true
description = "FastAPI"

[project.web.python.django]
description = "Django"

[project.web.go.gin]
default = true

[project.empty]
description = "Only platform.toml"

[cloud.aws.lambda]
description = "SAM"
languages = ["python"]
types = ["web"]

[cloud.docker]
description = "Dockerfile"
"""


@pytest.fixture
def matrix(tmp_path: Path) -> Matrix:
    path = tmp_path / "index.toml"
    path.write_text(INDEX)
    return Matrix.from_toml(path)


def test_types_and_stacks(matrix: Matrix):
    assert matrix.types() == ["empty", "web"]
    assert matrix.stacks("web") == ["go", "python"]
    assert matrix.stacks("empty") == []


def test_resolve_default(matrix: Matrix):
    leaf = matrix.resolve("web", "python", None)
    assert leaf.template == "fastapi"
    assert leaf.directory == "project/web/python/fastapi"


def test_resolve_explicit(matrix: Matrix):
    assert matrix.resolve("web", "python", "django").description == "Django"


def test_resolve_empty(matrix: Matrix):
    assert matrix.resolve("empty", None, None).directory == "project/empty"


def test_resolve_errors(matrix: Matrix):
    with pytest.raises(TemplateError):
        matrix.resolve("nope", None, None)
    with pytest.raises(TemplateError):
        matrix.resolve("web", None, None)
    with pytest.raises(TemplateError):
        matrix.resolve("web", "rust", None)
    with pytest.raises(TemplateError):
        matrix.resolve("web", "python", "flask")


def test_clouds(matrix: Matrix):
    assert [c.name for c in matrix.clouds] == ["aws/lambda", "docker"]
    lam = matrix.cloud("aws/lambda")
    assert lam.directory == "cloud/aws/lambda"
    assert lam.supports("web", "python")
    assert not lam.supports("web", "go")
    assert not lam.supports("library", "python")
    assert matrix.cloud("docker").supports("library", "rust")
    assert [c.name for c in matrix.clouds_for("web", "go")] == ["docker"]
    with pytest.raises(TemplateError):
        matrix.cloud("gcp/run")


def test_empty_index_sections(tmp_path: Path):
    path = tmp_path / "index.toml"
    path.write_text("[project]\n[cloud]\n")
    matrix = Matrix.from_toml(path)
    assert matrix.leaves == [] and matrix.clouds == []
