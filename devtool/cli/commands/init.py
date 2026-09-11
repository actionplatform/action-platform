"""`devtool init` command."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer

from devtool.logging import logger

TEMPLATES = Path(__file__).parents[2] / "templates"


def run(
    language: str = typer.Argument(..., help="Target stack (python, go, node, ...)"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
) -> None:
    """Bootstrap .code_quality/<lang>/ and devtool.toml."""
    cwd = Path.cwd()
    src = TEMPLATES / "code_quality" / language
    if not src.exists():
        raise typer.BadParameter(f"unknown language: {language}")

    dst_cq = cwd / ".code_quality" / language
    _copy_tree(src, dst_cq, force=force)
    logger.info("wrote %s", dst_cq)

    toml = cwd / "devtool.toml"
    if not toml.exists() or force:
        toml.write_text(_render_config(language, cwd.name))
        logger.info("wrote %s", toml)

    last = cwd / "LAST_VERSION"
    if not last.exists():
        last.write_text("0.1.0\n")
        logger.info("wrote %s", last)


def _copy_tree(src: Path, dst: Path, force: bool) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        rel = item.relative_to(src)
        _copy_file(item, dst / rel, force=force)


def _copy_file(src: Path, dst: Path, force: bool) -> None:
    if dst.exists() and not force:
        logger.warning("skip %s (exists)", dst)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _render_config(language: str, name: str) -> str:
    return (
        f'[project]\n'
        f'name = "{name}"\n'
        f'language = "{language}"\n\n'
        f'[source_host]\n'
        f'kind = "github"\n'
        f'repo = "owner/{name}"\n\n'
        f'[release]\n'
        f'strategy = "semver"\n'
        f'changelog = "conventional"\n'
    )
