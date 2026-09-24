"""action_platform.core.wiring — a wiring per facade; replacements never leak between wirings."""

from action_platform import ActionPlatform, Config
from action_platform.core.release.deploy import Deployer
from action_platform.core.release.release import Releaser
from action_platform.core.wiring import Wiring, wired
from tests.support import TempCase


class LoudReleaser(Releaser):
    pass


class LoudDeployer(Deployer):
    pass


class WiringIsolationTest(TempCase):
    def test_a_new_wiring_knows_the_core_classes(self):
        wiring = Wiring()

        self.assertIs(wiring.releaser, Releaser)
        self.assertIs(wiring.deployer, Deployer)
        self.assertIn("gitflow", wiring.slots())

    def test_a_replacement_stays_in_its_wiring(self):
        wiring = Wiring()

        wiring.replace("releaser", LoudReleaser, by="test")

        self.assertIs(wiring.releaser, LoudReleaser)
        self.assertEqual(wiring.origins(), {"releaser": "test"})
        self.assertIs(Wiring().releaser, Releaser)
        self.assertIs(wired.releaser, Releaser)

    def test_a_provided_default_stays_in_its_wiring(self):
        wiring = Wiring()

        wiring.provide("fake", LoudDeployer)

        self.assertIs(wiring.fake, LoudDeployer)
        self.assertNotIn("fake", Wiring().slots())

    def test_the_default_wiring_is_the_process_one(self):
        self.assertIs(Wiring.default(), wired)


class FacadeWiringTest(TempCase):
    def test_each_facade_resolves_through_its_own_wiring(self):
        wiring = Wiring()
        wiring.replace("releaser", LoudReleaser)
        wiring.replace("deployer", LoudDeployer)

        mine = ActionPlatform(Config(), repo_root=self.tmp_path, wiring=wiring)
        other = ActionPlatform(Config(), repo_root=self.tmp_path)

        self.assertIsInstance(mine.releaser, LoudReleaser)
        self.assertIsInstance(mine.deployer, LoudDeployer)
        self.assertIs(mine.deployer.wiring, wiring)
        self.assertIs(mine.flow.wiring, wiring)
        self.assertIs(type(other.releaser), Releaser)
        self.assertIs(other.wiring, wired)
