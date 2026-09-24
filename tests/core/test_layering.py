"""action_platform.core takes the configuration slices it needs; it never reaches for the settings singleton."""

import ast
import unittest
from pathlib import Path

import action_platform.core

CORE = Path(action_platform.core.__file__).parent


def imported_modules(path: Path) -> set[str]:
    names = set()

    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)

    return names


class CoreLayeringTest(unittest.TestCase):
    def test_no_core_module_imports_the_settings(self):
        offenders = [
            str(path.relative_to(CORE))
            for path in sorted(CORE.rglob("*.py"))
            if "action_platform.settings" in imported_modules(path)
        ]

        self.assertEqual(offenders, [])
