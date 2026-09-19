from pathlib import Path

from action_platform.plugins.installer import PipInstaller
from action_platform.testing.fixtures import TempCase


class UninstallFromTargetTest(TempCase):
    def test_record_entries_outside_the_target_are_ignored(self):
        root = Path(self.tmp_path) / "plugins"
        outside = Path(self.tmp_path) / "precious.txt"
        outside.write_text("keep")
        (root / "apx_x-1.0.dist-info").mkdir(parents=True)
        (root / "apx_x").mkdir()
        (root / "apx_x" / "__init__.py").write_text("")
        (root / "apx_x-1.0.dist-info" / "RECORD").write_text(
            "apx_x/__init__.py,,\n../precious.txt,,\n/etc/hosts,,\n"
        )

        out = PipInstaller(target=str(root))._remove_from_target("apx-x")

        self.assertEqual(out, "removed 1 file(s)")
        self.assertTrue(outside.exists())
        self.assertFalse((root / "apx_x").exists())

    def test_a_symlink_named_in_record_is_unlinked_not_followed(self):
        root = Path(self.tmp_path) / "plugins"
        target = Path(self.tmp_path) / "elsewhere"
        target.mkdir()
        (target / "data").write_text("x")
        (root / "apx_y-1.0.dist-info").mkdir(parents=True)
        (root / "link").symlink_to(target)
        (root / "apx_y-1.0.dist-info" / "RECORD").write_text("link,,\nlink/data,,\n")

        PipInstaller(target=str(root))._remove_from_target("apx-y")

        self.assertTrue((target / "data").exists())
        self.assertFalse((root / "link").exists())
