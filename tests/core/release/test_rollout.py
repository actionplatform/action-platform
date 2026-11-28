import unittest
from pathlib import Path

from action_platform.core.config import Config
from action_platform.core.exception import ConfigError, DeployError
from action_platform.core.release.deploy import Deployer
from action_platform.core.release.readiness import Readiness
from action_platform.core.rollout import (
    STRATEGIES,
    OperationResult,
    catalog,
    plan_for,
    strategy,
    strategy_check,
    support,
    validate_safety,
)
from action_platform.testing.fixtures import TempCase, platform_repo
from action_platform.testing.operations import (
    MockOperations,
    MockTarget,
    contract_problems,
    operation_context,
)


def kinds(steps) -> list[str]:
    return [s.kind for s in steps]


class PlanTest(unittest.TestCase):
    def test_recreate_is_deploy_then_retire(self):
        self.assertEqual(
            kinds(strategy("recreate").plan({})), ["deploy_new", "retire_old"]
        )
        self.assertEqual(strategy(None).id, "recreate")

    def test_rolling_replaces_in_batches_with_pauses_between(self):
        steps = strategy("rolling").plan({"batch_percent": 40, "pause_seconds": 10})

        self.assertEqual(
            [(s.kind, s.params.get("upto") or s.params.get("seconds")) for s in steps],
            [
                ("replace", 40),
                ("pause", 10),
                ("replace", 80),
                ("pause", 10),
                ("replace", 100),
            ],
        )

    def test_rolling_without_pause_has_no_pause_steps(self):
        steps = strategy("rolling").plan({"batch_percent": 50, "pause_seconds": 0})

        self.assertEqual(kinds(steps), ["replace", "replace"])

    def test_blue_green(self):
        steps = strategy("blue_green").plan({"keep_old_seconds": 30})

        self.assertEqual(
            kinds(steps),
            ["deploy_new", "health", "shift", "pause", "pause", "retire_old"],
        )
        self.assertEqual(steps[0].params, {"weight": 0})
        self.assertEqual(steps[2].params, {"weight": 100})
        self.assertEqual([s.params["seconds"] for s in steps[3:5]], [300, 30])

    def test_canary_default_steps(self):
        steps = strategy("canary").plan(None)

        self.assertEqual(
            [s.params["weight"] for s in steps if s.kind == "shift"], [5, 25, 50, 100]
        )
        self.assertEqual(
            kinds(steps)[:5], ["deploy_new", "shift", "pause", "health", "shift"]
        )
        self.assertEqual(kinds(steps)[-3:], ["shift", "health", "retire_old"])

    def test_shadow_never_promotes(self):
        steps = strategy("shadow").plan({"duration_seconds": 60})

        self.assertEqual(
            kinds(steps),
            ["deploy_new", "mirror", "pause", "health", "mirror", "retire_old"],
        )
        self.assertNotIn("shift", kinds(steps))
        self.assertEqual(steps[-1].params, {"retire": "new"})

    def test_manual_approval_waits_before_the_first_traffic_step(self):
        canary = strategy("canary").plan(None, {"manual_approval": True})
        recreate = strategy("recreate").plan({}, {"manual_approval": True})
        rolling = strategy("rolling").plan({}, {"manual_approval": True})

        self.assertEqual(kinds(canary)[:3], ["deploy_new", "approval", "shift"])
        self.assertEqual(kinds(recreate), ["approval", "deploy_new", "retire_old"])
        self.assertEqual(kinds(rolling)[0], "approval")

    def test_bake_waits_before_the_old_version_is_retired(self):
        steps = strategy("recreate").plan({}, {"bake_seconds": 45})

        self.assertEqual(kinds(steps), ["deploy_new", "pause", "retire_old"])
        self.assertEqual(steps[1].params, {"seconds": 45, "reason": "bake"})

    def test_configs_are_validated(self):
        for name, config in (
            ("rolling", {"batch_percent": 0}),
            ("rolling", {"batch_percent": 101}),
            ("rolling", {"batch": 5}),
            ("canary", {"steps": []}),
            ("canary", {"steps": [{"weight": 50, "pause_seconds": 1}]}),
            ("canary", {"steps": [{"weight": 101, "pause_seconds": 1}]}),
            ("shadow", {"duration_seconds": "long"}),
            ("recreate", {"x": 1}),
        ):
            with self.subTest(name=name, config=config):
                with self.assertRaises(ConfigError):
                    strategy(name).validate(config)

        with self.assertRaises(ConfigError):
            strategy("teleport")

        with self.assertRaises(ConfigError):
            validate_safety({"auto_rollback": "yes"})

    def test_defaults_are_filled_in(self):
        self.assertEqual(
            strategy("rolling").validate(None),
            {"batch_percent": 25, "pause_seconds": 60},
        )
        self.assertEqual(
            validate_safety(None),
            {"auto_rollback": True, "manual_approval": False, "bake_seconds": 0},
        )

    def test_the_catalog_serves_every_strategy_with_its_schema_and_needs(self):
        found = catalog()

        self.assertEqual(
            [s["id"] for s in found["strategies"]],
            ["recreate", "rolling", "blue_green", "canary", "shadow"],
        )
        self.assertEqual(found["strategies"][0]["needs"], [])
        self.assertIn("auto_rollback", found["safety_schema"]["properties"])


class SupportTest(unittest.TestCase):
    def test_a_target_without_operations_runs_recreate_only(self):
        target = MockTarget()

        self.assertEqual(
            {id: support(target, id).supported for id in STRATEGIES},
            {
                "recreate": True,
                "rolling": False,
                "blue_green": False,
                "canary": False,
                "shadow": False,
            },
        )
        self.assertIn("replace", support(target, "rolling").reason)

    def test_the_missing_operations_are_named(self):
        target = MockTarget(MockOperations({"deploy_new", "shift", "retire_old"}))
        found = support(target, "canary")

        self.assertFalse(found.supported)
        self.assertEqual(found.missing, ("health",))

    def test_a_native_strategy_is_supported_and_planned_as_one_step(self):
        target = MockTarget(MockOperations(set(), native={"canary"}))

        self.assertTrue(support(target, "canary").native)
        steps = plan_for(target, "canary", None, {"manual_approval": True})

        self.assertEqual(kinds(steps), ["approval", "native"])
        self.assertEqual(steps[1].params["strategy"], "canary")

    def test_planning_an_unsupported_strategy_is_refused(self):
        with self.assertRaises(DeployError):
            plan_for(MockTarget(), "blue_green")

    def test_strategy_check(self):
        ok = strategy_check([MockTarget(MockOperations())], "shadow")
        refused = strategy_check([MockTarget()], "shadow")

        self.assertTrue(ok.ok)
        self.assertFalse(refused.ok)
        self.assertIn("mirror", refused.detail)


class ContractTest(unittest.TestCase):
    def test_the_mock_operations_hold_the_contract(self):
        self.assertEqual(contract_problems(MockOperations(), operation_context()), [])
        self.assertEqual(
            contract_problems(MockOperations({"health"}), operation_context()), []
        )

    def test_a_raising_or_lying_target_is_reported(self):
        class Bad(MockOperations):
            def shift(self, ctx):
                raise RuntimeError("boom")

            def mirror(self, ctx):
                return OperationResult(True)

        problems = contract_problems(Bad({"health", "teleport"}), operation_context())

        self.assertTrue(any("teleport" in p for p in problems))
        self.assertTrue(any(p.startswith("shift raised") for p in problems))
        self.assertTrue(
            any(p.startswith("mirror is not in supports") for p in problems)
        )


class StrategyReadinessTest(TempCase):
    def setUp(self):
        super().setUp()
        self.repo = platform_repo(Path(self.tmp_path))

    def check(self, target, strategy=None):
        config = Config.from_dict({"scopes": [{"name": "dev", "criticality": "test"}]})
        config._deploy = [target]
        found = Readiness(config, self.repo, Deployer(config, self.repo)).check(
            "dev", version="1.2.3", strategy=strategy
        )

        return {c.id: c for c in found}

    def test_an_unsupported_strategy_blocks(self):
        checks = self.check(MockTarget(), "canary")

        self.assertFalse(checks["deploy.strategy"].ok)
        self.assertTrue(checks["deploy.strategy"].blocking)
        self.assertIn("deploy_new", checks["deploy.strategy"].detail)

    def test_a_supported_strategy_passes_and_none_adds_no_check(self):
        self.assertTrue(
            self.check(MockTarget(MockOperations()), "canary")["deploy.strategy"].ok
        )
        self.assertNotIn("deploy.strategy", self.check(MockTarget()))
