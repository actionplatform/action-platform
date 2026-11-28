"""The OpenAPI document, with every workspace route of an app also listed under its project — the gate serves both."""

import copy
from typing import Any, Callable

from fastapi import FastAPI

from app.core.access.rules import RENAMED, SERVED_BY_PROJECTS

LEGACY = "/api/apps/{id}"
NESTED = "/api/v1/projects/{project_id}/apps/{app_id}"


def _path_param(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "in": "path",
        "required": True,
        "schema": {"type": "string", "title": name.replace("_", " ").title()},
    }


def nested_paths(paths: dict[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}

    for path, item in paths.items():
        if path != LEGACY and not path.startswith(LEGACY + "/"):
            continue

        rest = path[len(LEGACY) :]
        renamed = {v: k for k, v in RENAMED.items()}.get(rest.lstrip("/"))

        if renamed:
            rest = f"/{renamed}"
        elif rest.lstrip("/") in SERVED_BY_PROJECTS:
            continue

        operations = {}

        for method, operation in item.items():
            if rest == "" and method != "get":
                continue

            moved = copy.deepcopy(operation)
            moved.pop("deprecated", None)
            moved["operationId"] = f"{operation['operationId']}_in_project"
            moved["parameters"] = [
                _path_param("project_id"),
                _path_param("app_id"),
                *(p for p in operation.get("parameters", []) if p.get("name") != "id"),
            ]
            operations[method] = moved

        if operations:
            nested[NESTED + rest] = operations

    return nested


def project_listing(paths: dict[str, Any]) -> dict[str, Any]:
    listing = paths.get("/api/apps", {}).get("get")

    if listing is None:
        return {}

    moved = copy.deepcopy(listing)
    moved.pop("deprecated", None)
    moved["operationId"] = f"{listing['operationId']}_in_project"
    moved["parameters"] = [_path_param("project_id"), *listing.get("parameters", [])]

    return {"/api/v1/projects/{project_id}/apps": {"get": moved}}


def install(app: FastAPI) -> None:
    build: Callable[[], dict[str, Any]] = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            schema = build()
            added = {
                **nested_paths(schema["paths"]),
                **project_listing(schema["paths"]),
            }

            for path, operations in added.items():
                schema["paths"].setdefault(path, {}).update(operations)
            app.openapi_schema = schema

        return app.openapi_schema

    app.openapi = openapi
