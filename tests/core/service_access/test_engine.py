import unittest
from unittest import mock

from action_platform.abc import Plugin
from action_platform.core.service_access import (
    Access,
    AccessError,
    Grant,
    Mapping,
    Person,
    spec,
)
from action_platform.plugins import Loaded, PluginState, Plugins, registry
from action_platform.testing.access import MemoryDirectory, MemoryProvider
from tests.support import TempCase

ANA = Person("ana@acme.dev", "u-ana", "Ana", "owner", ("platform",))
BEN = Person("ben@acme.dev", "u-ben", "Ben", "developer", ("backend",))


class World(unittest.TestCase):
    def setUp(self):
        self.vault = MemoryProvider("vault")
        self.vault.add("ana", "org", "admin")
        self.vault.add("ben", "org", "member")
        self.vault.add("ben", "repo/api", "write")
        self.vault.add("bot", "org", "admin")
        self.directory = MemoryDirectory([ANA, BEN])
        self.access = Access(self.directory, {"vault": self.vault})
        self.links = {
            "ana@acme.dev": {"vault": "ana"},
            "ben@acme.dev": {"vault": "ben"},
        }

    def imported(self):
        self.access.sync(apply=True, links=self.links)


class FirstSync(World):
    def test_first_sync_imports_and_changes_nothing(self):
        plan = self.access.sync(apply=True, links=self.links)

        self.assertTrue(plan.bootstrap)
        self.assertEqual(plan.changes, [])
        self.assertEqual(self.vault.applied, [])
        self.assertEqual(sorted(self.directory.mapping.imported), ["vault"])
        self.assertEqual(self.access.sync().changes, [])

    def test_dry_run_import_stores_nothing(self):
        plan = self.access.sync()

        self.assertTrue(plan.bootstrap and plan.dry_run)
        self.assertEqual(self.directory.saved, 0)
        self.assertIn("people", plan.mapping)

    def test_outsiders_are_kept_and_members_get_their_own_grants(self):
        self.imported()
        m = self.directory.mapping

        self.assertIn(
            {"service": "vault", "account": "bot", "resource": "org", "level": "admin"},
            m.keep,
        )
        self.assertIn(spec("vault", "repo/api", "write"), m.grants["ben@acme.dev"])

    def test_audit_after_import_has_no_drift_and_lists_levels(self):
        self.imported()
        row = self.access.audit().services[0]

        self.assertTrue(row.ok and row.imported and not row.drift)
        self.assertEqual(row.outside_accounts, ["bot"])
        self.assertEqual(row.levels["repo"], ["read", "write"])

    def test_operations_before_the_import_are_refused(self):
        with self.assertRaises(AccessError):
            self.access.grant("ben@acme.dev", "vault", "repo/web", "read")


class Changes(World):
    def test_grant_touches_only_that_person_and_adds_companions(self):
        self.vault.grants = [g for g in self.vault.grants if g.account != "ben"]
        self.vault.add("ana", "repo/api", "write")
        self.imported()
        self.vault.add("stranger", "org", "member")

        plan = self.access.grant(
            "ben@acme.dev", "vault", "repo/web", "read", account="ben", apply=True
        )

        self.assertEqual(
            sorted((c.account, c.resource, c.status) for c in plan.changes),
            [("ben", "org", "applied"), ("ben", "repo/web", "applied")],
        )
        self.assertIn(Grant("vault", "stranger", "org", "member"), self.vault.grants)

    def test_dry_run_grant_writes_nothing(self):
        self.imported()
        plan = self.access.grant("ben@acme.dev", "vault", "repo/web", "read")

        self.assertTrue(plan.dry_run)
        self.assertEqual(self.vault.applied, [])
        self.assertTrue(all(c.status == "planned" for c in plan.changes))

    def test_grant_refuses_unknown_levels(self):
        self.imported()

        with self.assertRaises(AccessError):
            self.access.grant("ben@acme.dev", "vault", "repo/web", "owner")

    def test_revoke_names_what_the_team_still_grants(self):
        self.imported()
        mapping = self.directory.load()
        mapping.teams["backend"] = [spec("vault", "repo/api", "write")]
        self.directory.save(mapping)

        plan = self.access.revoke("ben@acme.dev", "vault", "repo/api", apply=True)

        self.assertIn("team:backend", plan.note)
        self.assertEqual(plan.changes, [])

    def test_offboard_removes_every_grant_but_never_the_last_admin(self):
        self.imported()
        self.vault.grants = [g for g in self.vault.grants if g.account != "bot"]

        plan = self.access.offboard("ana@acme.dev", apply=True)

        self.assertEqual([c.status for c in plan.changes], ["refused"])

    def test_a_refused_organization_change_holds_the_rest_of_that_account(self):
        self.vault.add("ana", "repo/api", "write")
        self.imported()
        self.vault.grants = [g for g in self.vault.grants if g.account != "bot"]

        plan = self.access.offboard("ana@acme.dev", apply=True)

        self.assertEqual(
            sorted((c.resource, c.status) for c in plan.changes),
            [("org", "refused"), ("repo/api", "refused")],
        )
        self.assertIn(Grant("vault", "ana", "repo/api", "write"), self.vault.grants)
        self.assertIn(Grant("vault", "ana", "org", "admin"), self.vault.grants)

        ben = self.access.offboard(
            "ben@acme.dev", apply=True, remove_from_platform=True
        )

        self.assertTrue(all(c.status == "applied" for c in ben.changes))
        self.assertFalse([g for g in self.vault.grants if g.account == "ben"])
        self.assertEqual(self.directory.removed, ["ben@acme.dev"])
        self.assertNotIn("ben@acme.dev", self.directory.mapping.people)

    def test_leaving_the_organization_is_drift(self):
        self.imported()
        self.directory.members = [ANA]

        drift = self.access.audit().services[0].drift

        self.assertEqual(
            sorted((c.action, c.account, c.resource) for c in drift),
            [("remove", "ben", "org"), ("remove", "ben", "repo/api")],
        )

    def test_a_failing_service_is_reported_not_emptied(self):
        self.imported()
        self.vault.refuse.add("ben")
        self.directory.members = [ANA]

        plan = self.access.sync(apply=True)

        self.assertTrue(all(c.status == "failed" for c in plan.changes))
        self.assertIn(Grant("vault", "ben", "org", "member"), self.vault.grants)


class Unavailable(unittest.TestCase):
    def test_a_service_that_could_not_be_built_shows_in_the_audit(self):
        access = Access(
            MemoryDirectory([ANA], Mapping(imported={"vault": "now"})),
            {"vault": MemoryProvider("vault")},
            {"jenkins": "jenkins: set url"},
        )

        rows = {r.service: r for r in access.audit().services}

        self.assertFalse(rows["jenkins"].ok)
        self.assertEqual(rows["jenkins"].error, "jenkins: set url")


class Vault(Plugin):
    slug = "vault"

    def access(self, options):
        if not options.get("url"):
            return None

        if not options.get("token"):
            raise AccessError("vault: set token")

        return MemoryProvider("vault")


class Silent(Plugin):
    slug = "silent"


class Providers(TempCase):
    def plugins(self):
        return Plugins(
            [Loaded(Vault(), "apx-vault", "1.0"), Loaded(Silent(), "apx-silent")],
            PluginState(file=self.tmp_path / "plugins.json"),
        )

    def options(self, values):
        class Opts:
            def get(self, key, default=None):
                return values.get(key, default)

        return lambda slug: Opts()

    def test_only_plugins_whose_options_configure_access_bring_a_provider(self):
        plugins = self.plugins()

        self.assertEqual(plugins.access_providers(self.options({})), ({}, {}))

        providers, errors = plugins.access_providers(self.options({"url": "u"}))

        self.assertEqual((providers, errors), ({}, {"vault": "vault: set token"}))

        providers, _ = plugins.access_providers(
            self.options({"url": "u", "token": "t"})
        )

        self.assertEqual(list(providers), ["vault"])

    def test_a_disabled_plugin_brings_nothing_and_rows_say_who_offers_access(self):
        plugins = self.plugins()
        rows = {r["slug"]: r["access"] for r in plugins.rows()}

        self.assertEqual(rows, {"silent": False, "vault": True})

        plugins.disable("vault")

        self.assertEqual(
            plugins.access_providers(self.options({"url": "u", "token": "t"})),
            ({}, {}),
        )


class OldAccess(Plugin):
    slug = "access"


class Reserved(unittest.TestCase):
    def test_the_access_slug_is_refused_with_the_way_out(self):
        ep = mock.Mock(dist=mock.Mock(version="0.1.2"), load=lambda: OldAccess)
        ep.name = "access"
        ep.dist.name = "apx-access"
        self.addCleanup(registry.FAILURES.pop, "access", None)

        with mock.patch.object(registry, "entry_points", lambda group: [ep]):
            found = Plugins.find()

        self.assertEqual(found, [])
        self.assertIn("apx-github", registry.FAILURES["access"])
