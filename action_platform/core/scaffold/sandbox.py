"""The process a template renders in: `python -I -m action_platform.core.scaffold.sandbox` reads one request on stdin, renders it with a sandboxed Jinja environment and writes the outcome to the request's `result` file."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from cookiecutter import generate, hooks, prompt
from cookiecutter.environment import ExtensionLoaderMixin
from cookiecutter.exceptions import CookiecutterException
from cookiecutter.main import cookiecutter
from jinja2 import StrictUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment


class SandboxedStrictEnvironment(ExtensionLoaderMixin, SandboxedEnvironment):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(undefined=StrictUndefined, **kwargs)


def sandboxed_env(context: dict[str, Any]) -> SandboxedStrictEnvironment:
    envvars = context.get("cookiecutter", {}).get("_jinja2_env_vars", {})

    return SandboxedStrictEnvironment(
        context=context, keep_trailing_newline=True, **envvars
    )


def render(request: dict[str, Any]) -> str:
    for module in (generate, hooks, prompt):
        setattr(module, "create_env_with_context", sandboxed_env)

    return cookiecutter(
        request["template"],
        no_input=True,
        extra_context=request["context"],
        output_dir=request["output"],
        default_config=True,
        accept_hooks=request["trusted"],
    )


def main() -> int:
    request = json.loads(sys.stdin.read())
    result = Path(request["result"])

    try:
        outcome = {"project": render(request)}
    except (CookiecutterException, TemplateError, OSError, ValueError) as e:
        outcome = {"error": str(e) or type(e).__name__}

    result.write_text(json.dumps(outcome))

    return 0 if "project" in outcome else 1


if __name__ == "__main__":
    sys.exit(main())
