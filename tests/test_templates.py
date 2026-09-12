"""Template matrix tests."""

from pathlib import Path

import pytest

from action_platform.core.exception import TemplateError
from action_platform.core.templates import Matrix

INDEX = """
[web.python.fastapi]
default = true
description = "FastAPI"

[web.python.django]
description = "Django"

[web.go.gin]
default = true

[empty]
description = "Only platform.toml"
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
    assert leaf.directory == "web/python/fastapi"


def test_resolve_explicit(matrix: Matrix):
    assert matrix.resolve("web", "python", "django").description == "Django"


def test_resolve_empty(matrix: Matrix):
    assert matrix.resolve("empty", None, None).directory == "empty"


def test_resolve_errors(matrix: Matrix):
    with pytest.raises(TemplateError):
        matrix.resolve("nope", None, None)
    with pytest.raises(TemplateError):
        matrix.resolve("web", None, None)
    with pytest.raises(TemplateError):
        matrix.resolve("web", "rust", None)
    with pytest.raises(TemplateError):
        matrix.resolve("web", "python", "flask")
