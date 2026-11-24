"""Plugins: found, switched on and off, tools prefixed and guarded, overlays merged, hooks called."""

import asyncio
import json
import unittest
from unittest import mock
from pathlib import Path

from action_platform.abc import Connection, Plugin
from action_platform.core.flow import gitflow
from action_platform.core.wiring import wired
from action_platform.core.scaffold.catalog import Matrix, with_plugin_clouds
from action_platform.plugins import (
    Credential,
    FileOptions,
    Loaded,
    PluginError,
    PluginState,
    Plugins,
    registry,
)
from tests.mcp.support import HAS_MCP
from tests.support import TempCase


class Example(Plugin):
    slug = "example"
    description = "Says hello"
    needs = ["net: example.com"]

    def __init__(self) -> None:
        self.seen: list = []
        self.root: Path | None = None

    @property
    def overlays(self):
        return self.root

    def register(self, surface) -> None:
        surface.core.replace("gitflow_rules", StrictRules)

        if surface.mcp is None:
            return

        @surface.mcp.tool()
        def hello(name: str = "world") -> dict:
            return {"greeting": f"hello {name}"}

    def after_release(self, ctx) -> None:
        self.seen.append(("release", ctx))

    def after_deploy(self, results) -> None:
        raise RuntimeError("boom")


class StrictRules(gitflow.Rules):
    kinds = {"feature", "hotfix"}


class PluginsTest(TempCase):
    def setUp(self):
        super().setUp()
        self.state = PluginState(file=Path(self.tmp_path) / "plugins.json")
        self.example = Example()
        self.plugins = Plugins(
            [Loaded(self.example, "apx-example", "1.0.0")],
            self.state,
        )
        registry._current = self.plugins
        self.addCleanup(registry.reset)
        self.addCleanup(wired.restore, "gitflow_rules")

    def test_a_plugins_logger_reaches_the_job_sink(self):
        import logging

        from action_platform.logging import capture

        seen: list[str] = []
        loaded = Loaded(self.example, "apx-example", "1.0.0")

        self.assertEqual(loaded.module, "tests")

        with capture(seen.append):
            self.example.logger.info("pushing %s", "image")
            logging.getLogger("tests.plugins.deep").info("nested too")

        self.assertEqual(seen, ["pushing image", "nested too"])

    def test_discovery_attaches_every_plugin_found(self):
        import logging

        from action_platform.logging import capture

        ep = mock.Mock()
        ep.name = "example"
        ep.load.return_value = Example
        ep.dist = None
        seen: list[str] = []

        with mock.patch.object(registry, "entry_points", return_value=[ep]):
            found = registry.Plugins.find()

        with capture(seen.append):
            logging.getLogger("tests.anything").info("hello")

        self.assertEqual([f.slug for f in found], [self.example.slug])
        self.assertEqual(seen, ["hello"])

    def test_rows_and_flags_persist(self):
        self.assertEqual(self.plugins.rows()[0]["enabled"], True)

        self.plugins.disable("example")

        self.assertEqual(self.plugins.rows()[0]["enabled"], False)
        self.assertEqual(self.plugins.disabled_packages(), {"apx-example"})
        self.assertEqual(
            json.loads(self.state.file.read_text())["plugins"]["example"]["enabled"],
            False,
        )
        self.assertEqual(PluginState.load(self.state.file).enabled("example"), False)

    def test_a_removed_plugin_cannot_be_enabled_and_is_forgotten_by_the_restart(self):
        self.state.mark_removed("example")

        with self.assertRaises(PluginError) as caught:
            self.plugins.enable("example")

        self.assertIn("removed", str(caught.exception))
        self.assertEqual(self.state.restart_pending(), ["example"])

        self.state.clear_restart()

        self.assertEqual(self.state.plugins, {})

    def test_discovery_forgets_a_removed_plugin_whose_package_is_gone(self):
        self.state.mark_removed("gone")

        with mock.patch.object(Plugins, "find", staticmethod(lambda known=None: [])):
            found = Plugins.discover(PluginState.load(self.state.file))

        self.assertEqual(found.state.plugins, {})
        self.assertEqual(PluginState.load(self.state.file).plugins, {})

    def test_unknown_slug_is_a_readable_error(self):
        with self.assertRaises(PluginError) as caught:
            self.plugins.enable("nope")

        self.assertIn("installed: example", str(caught.exception))

    @unittest.skipUnless(HAS_MCP, "mcp is not installed")
    def test_tools_come_out_prefixed_and_guarded(self):
        from action_platform.mcp import server

        mcp = server.build()
        names = {t.name for t in asyncio.run(mcp.list_tools())}

        self.assertIn("example_hello", names)

        result = asyncio.run(mcp.call_tool("example_hello", {"name": "you"}))

        self.assertEqual(json.loads(result.content[0].text)["greeting"], "hello you")

        self.plugins.disable("example")

        with self.assertRaises(Exception) as caught:
            asyncio.run(mcp.call_tool("example_hello", {}))

        self.assertIn("disabled", str(caught.exception))

    def test_plugin_overlay_replaces_the_repository_cloud(self):
        root = Path(self.tmp_path) / "overlays"
        (root / "cloud" / "fly").mkdir(parents=True)
        (root / "index.json").write_text(
            json.dumps(
                {"clouds": [{"id": "fly", "description": "Fly.io", "types": ["web"]}]}
            )
        )
        self.example.root = root
        matrix = Matrix.from_dict(
            {"clouds": [{"id": "fly", "description": "old"}, {"id": "docker"}]}
        )

        merged = with_plugin_clouds(matrix)
        fly = merged.cloud("fly")

        self.assertEqual({c.name for c in merged.clouds}, {"fly", "docker"})
        self.assertEqual(fly.description, "Fly.io")
        self.assertEqual(fly.source, "example")
        self.assertEqual(fly.root, root)

        self.plugins.disable("example")

        self.assertEqual(
            with_plugin_clouds(Matrix.from_dict({"clouds": []})).clouds, []
        )

    def test_a_plugin_replaces_a_slot_and_disabling_restores_it(self):
        self.plugins.register()

        self.assertIs(wired.gitflow_rules, StrictRules)
        self.assertIsNotNone(gitflow.check_branch("chore/1"))
        self.assertEqual(self.plugins.rows()[0]["replaces"], ["gitflow_rules"])

        self.plugins.disable("example")

        self.assertIs(wired.gitflow_rules, gitflow.Rules)
        self.assertIsNone(gitflow.check_branch("chore/1"))

        self.plugins.enable("example")

        self.assertIs(wired.gitflow_rules, StrictRules)

    def test_a_replacement_must_subclass_the_default(self):
        with self.assertRaises(Exception) as caught:
            wired.replace("releaser", StrictRules)

        self.assertIn("must subclass", str(caught.exception))

    def test_hooks_reach_enabled_plugins_and_failures_do_not_propagate(self):
        self.plugins.after_release("ctx")
        self.plugins.after_deploy([])

        self.assertEqual(self.example.seen, [("release", "ctx")])

        self.plugins.disable("example")
        self.plugins.after_release("again")

        self.assertEqual(len(self.example.seen), 1)


class PlainOverlayTest(TempCase):
    def test_an_overlay_without_cookiecutter_is_copied_as_is(self):
        from action_platform.core.scaffold.scaffolder import apply_cloud
        from action_platform.core.scaffold.catalog import Cloud

        root = Path(self.tmp_path) / "overlays"
        (root / "cloud" / "plain" / "deploy").mkdir(parents=True)
        (root / "cloud" / "plain" / "DEPLOY.md").write_text("# plain\n")
        (root / "cloud" / "plain" / "deploy" / "run.sh").write_text("echo hi\n")
        project = Path(self.tmp_path) / "proj"
        project.mkdir()
        (project / "platform.toml").write_text(
            '[project]\nname = "proj"\ntype = "web"\nlanguage = "python"\n'
        )

        apply_cloud(root, Cloud("plain", root=root), project)

        self.assertEqual((project / "DEPLOY.md").read_text(), "# plain\n")
        self.assertTrue((project / "deploy" / "run.sh").exists())
        self.assertIn('target = "plain"', (project / "platform.toml").read_text())


class OptionsTest(TempCase):
    def test_file_options_round_trip(self):
        from action_platform.plugins import FileOptions

        options = FileOptions("example", Path(self.tmp_path))

        self.assertIsNone(options.get("channel"))
        self.assertEqual(options.get("channel", "#dev"), "#dev")

        options.set("channel", "#ops")
        options.set("retries", 3)

        self.assertEqual(options.all(), {"channel": "#ops", "retries": 3})
        self.assertEqual(FileOptions("example", Path(self.tmp_path)).get("retries"), 3)

        options.delete("channel")
        options.delete("nope")

        self.assertEqual(options.all(), {"retries": 3})

    def test_the_surface_carries_the_plugin_options(self):
        from action_platform.plugins import FileOptions, Loaded, PluginState, Plugins

        seen = {}

        class Remembering(Plugin):
            slug = "mem"

            def register(self, surface) -> None:
                surface.options.set("hello", "world")
                seen["value"] = surface.options.get("hello")

        plugins = Plugins(
            [Loaded(Remembering(), "apx-mem", "1.0.0")],
            PluginState(file=Path(self.tmp_path) / "p.json"),
        )
        plugins.options_factory = lambda slug: FileOptions(slug, Path(self.tmp_path))
        plugins.register()

        self.assertEqual(seen, {"value": "world"})
        self.assertEqual(
            FileOptions("mem", Path(self.tmp_path)).all(), {"hello": "world"}
        )


class Reader(Plugin):
    slug = "reader"
    connections = [
        Connection("github", ("admin:org", "repo"), (("members", "write"),)),
    ]


class Lister(Plugin):
    slug = "lister"
    connections = [
        Connection("github", ("repo", "read:org"), (("members", "read"),)),
        Connection("sentry", ("org:read",)),
    ]


class ConnectionsTest(TempCase):
    def setUp(self):
        super().setUp()
        self.plugins = Plugins(
            [Loaded(Reader()), Loaded(Lister())],
            PluginState(file=Path(self.tmp_path) / "plugins.json"),
        )

    def test_scopes_are_the_union_of_the_enabled_plugins(self):
        self.assertEqual(
            self.plugins.connection_scopes("github"), ["admin:org", "repo", "read:org"]
        )
        self.assertEqual(self.plugins.connection_scopes("sentry"), ["org:read"])
        self.assertEqual(self.plugins.connection_scopes("gitlab"), [])

    def test_the_strongest_permission_wins(self):
        self.assertEqual(
            self.plugins.connection_permissions("github"), {"members": "write"}
        )

    def test_a_disabled_plugin_asks_for_nothing(self):
        self.plugins.state.set_enabled("reader", False)

        self.assertEqual(self.plugins.connection_scopes("github"), ["repo", "read:org"])
        self.assertFalse(self.plugins.declares("reader", "github"))

    def test_a_plugin_reads_only_what_it_declares(self):
        self.assertTrue(self.plugins.declares("lister", "sentry"))
        self.assertFalse(self.plugins.declares("reader", "sentry"))

    def test_rows_list_the_connections(self):
        row = next(r for r in self.plugins.rows() if r["slug"] == "reader")

        self.assertEqual(row["connections"][0]["permissions"], {"members": "write"})

    def test_options_hand_no_credential_on_a_machine(self):
        self.assertIsNone(FileOptions("reader").credential("github"))

    def test_a_credential_never_shows_its_token(self):
        self.assertNotIn("s3cret", repr(Credential("github", "s3cret", "me")))


class Notifier(Plugin):
    slug = "notifier"

    def routes(self, event, options) -> list[str]:
        return ["chat"] if options.get("chat") else []

    def deliver(self, event, route, options) -> None:
        pass


class EventsTest(TempCase):
    def setUp(self):
        super().setUp()
        self.state = PluginState(file=Path(self.tmp_path) / "plugins.json")
        self.plugins = Plugins(
            [
                Loaded(Example(), "apx-example", "1.0.0"),
                Loaded(Notifier(), "apx-notifier", "1.0.0"),
            ],
            self.state,
        )
        self.addCleanup(wired.restore, "gitflow_rules")

    def test_only_a_plugin_that_routes_events_listens(self):
        self.assertEqual([r.slug for r in self.plugins.listeners()], ["notifier"])
        self.assertEqual(
            {r["slug"]: r["events"] for r in self.plugins.rows()},
            {"example": False, "notifier": True},
        )

    def test_a_disabled_plugin_stops_listening(self):
        self.plugins.disable("notifier")

        self.assertEqual(self.plugins.listeners(), [])

    def test_an_event_survives_a_round_trip_through_json(self):
        from action_platform.abc import Event

        event = Event(
            "deployment.failed",
            "acme",
            "shop",
            "api",
            actor="ana",
            payload={"stage": "prod", "version": "1.2.0"},
            url="https://ap.test/projects/p/apps/a/deployments",
            id="e1",
            at="2026-11-24T20:00:00",
        )

        again = Event.from_dict(json.loads(json.dumps({**event.as_dict(), "x": 1})))

        self.assertEqual(again, event)
