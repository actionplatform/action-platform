from __future__ import annotations


from pydantic import BaseModel


class Version(BaseModel):
    version: str


class MatrixProject(BaseModel):
    type: str
    stack: str
    template: str
    default: bool
    description: str


class MatrixCloud(BaseModel):
    name: str
    types: list[str]
    languages: list[str]
    description: str


class MatrixService(BaseModel):
    name: str
    providers: list[str]
    description: str


class Matrix(BaseModel):
    projects: list[MatrixProject]
    clouds: list[MatrixCloud]
    services: list[MatrixService]


class GitflowRules(BaseModel):
    kinds: list[str]
    protected: list[str]
    types: list[str]
