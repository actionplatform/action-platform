from __future__ import annotations

import tempfile
from pathlib import Path

from tests.test_access import GateCase


class ConfigStoreAdoptTest(GateCase):
    def setUp(self):
        super().setUp()
        from app.repositories.configuration.config_store import ConfigStore

        self.store = ConfigStore(self.app.state.db)
        self.root = Path(tempfile.mkdtemp())
        self.file = self.root / "platform.toml"

    def write(self, text: str) -> None:
        self.file.write_text(text)

    def test_first_sight_imports_and_remembers_the_file(self):
        self.write('[project]\nname = "x"\n')

        self.assertTrue(self.store.adopt("r1", self.root))
        self.assertEqual(self.store.get("r1")["project"], {"name": "x"})
        self.assertFalse(self.store.adopt("r1", self.root))

    def test_a_changed_file_replaces_what_the_platform_keeps(self):
        self.write('[project]\nname = "x"\n')
        self.store.adopt("r2", self.root)
        self.store.set(
            "r2", {"project": {"name": "x"}, "deploy": {"target": "aws/lambda"}}
        )

        self.assertFalse(self.store.adopt("r2", self.root))
        self.assertEqual(self.store.get("r2")["deploy"], {"target": "aws/lambda"})

        self.write(
            '[project]\nname = "x"\n\n[[deploy.targets]]\nname = "pypi"\nkind = "pypi"\n'
        )

        self.assertTrue(self.store.adopt("r2", self.root))
        self.assertEqual(
            self.store.get("r2")["deploy"],
            {"targets": [{"name": "pypi", "kind": "pypi"}]},
        )

    def test_export_marks_the_file_as_seen(self):
        self.write('[project]\nname = "x"\n')
        self.store.adopt("r3", self.root)
        self.store.set(
            "r3", {"project": {"name": "x"}, "release": {"strategy": "semver"}}
        )
        self.store.export("r3", self.root)

        self.assertFalse(self.store.adopt("r3", self.root))
        self.assertEqual(self.store.get("r3")["release"], {"strategy": "semver"})
