"""This directory *is* the `action_platform_api` package: every subpackage here is installed under that name."""

from setuptools import find_packages, setup

setup(
    package_dir={"action_platform_api": "."},
    packages=["action_platform_api"]
    + [
        f"action_platform_api.{p}"
        for p in find_packages(where=".", exclude=["tests", "tests.*"])
    ],
)
