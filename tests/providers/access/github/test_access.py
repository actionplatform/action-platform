import unittest

from action_platform.core.service_access import (
    Access,
    AccessError,
    Grant,
    Mapping,
    Op,
    Person,
    spec,
)
from action_platform.testing.access import MemoryDirectory

from action_platform.providers.access.github.provider import GitHubProvider
from action_platform.testing.github import FakeGitHub

ANA = Person("ana@acme.dev", "u-ana", "Ana", "owner", ("platform",))
BEN = Person("ben@acme.dev", "u-ben", "Ben", "developer", ("backend",))


class World(unittest.TestCase):
    def setUp(self):
        self.github = FakeGitHub()
        self.github.members = {"ana": "admin", "ben": "member", "acme-bot": "admin"}
        self.github.teams = {
            "core": {"members": {"ana": "maintainer"}, "repos": {"api": "push"}}
        }
        self.github.repo("api")
        self.github.repo("site")
        self.github.repos["api"] = {"ben": "push"}
        self.directory = MemoryDirectory([ANA, BEN])
        self.provider = GitHubProvider("acme", "t", http=self.github)
        self.access = Access(self.directory, {"github": self.provider})
        self.links = {
            "ana@acme.dev": {"github": "ana"},
            "ben@acme.dev": {"github": "ben"},
        }

    def bootstrapped(self):
        self.access.sync(apply=True, links=self.links)


class FirstSync(World):
    def test_first_sync_imports_and_changes_nothing(self):
        plan = self.access.sync(apply=True)

        self.assertTrue(plan.bootstrap)
        self.assertEqual(plan.changes, [])
        self.assertEqual(self.github.writes(), [])
        self.assertEqual(sorted(self.directory.mapping.imported), ["github"])
        self.assertEqual(self.access.sync().changes, [])

    def test_dry_run_bootstrap_stores_nothing(self):
        plan = self.access.sync()

        self.assertTrue(plan.bootstrap and plan.dry_run)
        self.assertEqual(self.directory.saved, 0)

    def test_outsiders_are_kept_and_personal_grants_recorded(self):
        self.bootstrapped()
        m = self.directory.mapping
        kept = {(r["service"], r["account"]) for r in m.keep}

        self.assertIn(("github", "acme-bot"), kept)
        self.assertIn(("github", "team:core"), kept)
        self.assertIn(spec("github", "repo/api", "push"), m.grants["ben@acme.dev"])

    def test_audit_after_bootstrap_shows_no_drift(self):
        self.bootstrapped()
        audit = self.access.audit()

        self.assertTrue(all(s.ok and not s.drift for s in audit.services))


class Changes(World):
    def test_grant_touches_only_that_person(self):
        self.bootstrapped()
        self.github.members["stranger"] = "member"

        plan = self.access.grant(
            "ben@acme.dev", "github", "repo/site", "pull", apply=True
        )

        self.assertEqual(
            [(c.action, c.account, c.resource, c.status) for c in plan.changes],
            [("add", "ben", "repo/site", "applied")],
        )
        self.assertEqual(self.github.repos["site"], {"ben": "pull"})
        self.assertIn("stranger", self.github.members)
        self.assertEqual(
            [w[:2] for w in self.github.writes()],
            [("PUT", "repos/acme/site/collaborators/ben")],
        )

    def test_dry_run_writes_nothing(self):
        self.bootstrapped()

        plan = self.access.grant("ben@acme.dev", "github", "repo/site", "push")

        self.assertEqual(plan.changes[0].action, "add")
        self.assertEqual(self.github.writes(), [])
        self.assertEqual(self.github.repos["site"], {})

    def test_unknown_levels_are_refused(self):
        self.bootstrapped()

        with self.assertRaisesRegex(AccessError, "takes pull, triage, push"):
            self.access.grant("ben@acme.dev", "github", "repo/api", "owner")

    def test_drift_is_applied_and_converges(self):
        self.bootstrapped()
        self.directory.mapping.grants["ben@acme.dev"].append(
            spec("github", "repo/site", "triage")
        )

        plan = self.access.sync(apply=True)

        self.assertEqual(
            [(c.resource, c.status) for c in plan.changes], [("repo/site", "applied")]
        )
        self.assertEqual(self.github.repos["site"], {"ben": "triage"})
        self.assertEqual(self.access.sync().changes, [])

    def test_leaving_the_organization_is_drift(self):
        self.bootstrapped()
        self.directory.members = [ANA]

        drift = {
            (c.account, c.action) for s in self.access.audit().services for c in s.drift
        }

        self.assertIn(("ben", "remove"), drift)

    def test_revoke_removes_the_collaborator(self):
        self.bootstrapped()

        plan = self.access.revoke("ben@acme.dev", "github", "repo/api", apply=True)

        self.assertEqual(self.github.repos["api"], {})
        self.assertEqual(plan.changes[0].action, "remove")

    def test_offboard_removes_every_grant(self):
        self.bootstrapped()

        plan = self.access.offboard("ben@acme.dev", apply=True)

        self.assertTrue(all(c.status == "applied" for c in plan.changes))
        self.assertNotIn("ben", self.github.members)
        self.assertEqual(self.github.repos["api"], {})

    def test_the_last_admin_is_refused(self):
        self.github.members = {"ana": "admin", "ben": "member"}
        self.bootstrapped()

        plan = self.access.offboard("ana@acme.dev", apply=True)

        self.assertEqual(
            {(c.resource, c.status) for c in plan.changes if c.resource == "org"},
            {("org", "refused")},
        )
        self.assertEqual(self.github.members["ana"], "admin")

    def test_a_team_grant_brings_organization_membership(self):
        self.bootstrapped()
        self.directory.members.append(
            Person("cy@acme.dev", "u-cy", "Cy", "developer", ("backend",))
        )
        self.directory.mapping.people["cy@acme.dev"] = {"github": "cy"}
        self.directory.mapping.teams["backend"] = [
            spec("github", "team/backend", "member")
        ]

        self.access.sync(apply=True)

        self.assertEqual(self.github.members["cy"], "member")
        self.assertEqual(
            self.github.teams["backend"]["members"],
            {"ben": "member", "cy": "member"},
        )
        self.assertEqual(self.access.sync().changes, [])

    def test_accounts_match_whatever_the_case(self):
        self.access.sync(apply=True, links={"ana@acme.dev": {"github": "ANA"}})

        self.assertEqual(self.directory.mapping.people["ana@acme.dev"]["github"], "ana")
        self.directory.mapping.people["ana@acme.dev"]["github"] = "Ana"

        self.assertEqual(self.access.sync().changes, [])


class Guard(unittest.TestCase):
    def test_the_last_admin_is_refused_whatever_the_case(self):
        provider = GitHubProvider("acme", "t", http=FakeGitHub())
        op = Op("change", Grant("github", "Octocat", "org", "member"), "admin")
        live = [
            Grant("github", "octocat", "org", "admin"),
            Grant("github", "hubot", "org", "member"),
        ]

        self.assertIn(op, provider.guard([op], live))

    def test_another_admin_makes_a_demotion_safe(self):
        provider = GitHubProvider("acme", "t", http=FakeGitHub())
        op = Op("change", Grant("github", "Octocat", "org", "member"), "admin")
        live = [
            Grant("github", "octocat", "org", "admin"),
            Grant("github", "hubot", "org", "admin"),
        ]

        self.assertEqual(provider.guard([op], live), {})


class Reads(unittest.TestCase):
    def test_team_repositories_are_team_accounts(self):
        fake = FakeGitHub()
        fake.teams = {"core": {"members": {}, "repos": {"api": "pull"}}}

        grants = GitHubProvider("acme", "t", http=fake).read()

        self.assertEqual(grants, [Grant("github", "team:core", "repo/api", "pull")])

    def test_pending_invitations_count(self):
        fake = FakeGitHub()
        fake.invited = {"newbie": "member", "boss": "admin"}

        grants = GitHubProvider("acme", "t", http=fake).read()

        self.assertEqual(
            grants,
            [
                Grant("github", "boss", "org", "admin"),
                Grant("github", "newbie", "org", "member"),
            ],
        )

    def test_listings_follow_the_next_link(self):
        fake = FakeGitHub(page=2)
        fake.members = {f"u{n}": "member" for n in range(5)}

        grants = GitHubProvider("acme", "t", http=fake).read()

        self.assertEqual(len(grants), 5)

    def test_a_role_name_beats_the_permission_flags(self):
        fake = FakeGitHub()
        fake.repo("api")
        fake.repos["api"] = {"ben": "maintain"}

        grants = GitHubProvider("acme", "t", http=fake).read()

        self.assertEqual(grants, [Grant("github", "ben", "repo/api", "maintain")])

    def test_a_refusal_names_the_call_and_never_the_token(self):
        fake = FakeGitHub()
        provider = GitHubProvider("acme", "secret-token", http=fake)

        with self.assertRaisesRegex(AccessError, "github: PUT"):
            provider.apply(Op("add", Grant("github", "ben", "repo/nope", "pull")))

        self.assertNotIn("secret-token", str(fake.calls))


class Mappings(unittest.TestCase):
    def test_mapping_round_trips(self):
        m = Mapping(people={"a@x": {"github": "a"}}, imported={"github": "t"})

        self.assertEqual(Mapping.of(m.as_dict()), m)


class TokenChecks(World):
    def test_a_classic_token_without_admin_org_reads_but_cannot_change(self):
        self.github.scopes = "read:org, repo"

        self.assertTrue(self.provider.read())

        with self.assertRaisesRegex(
            AccessError, "lacks the admin:org scope; reconnect GitHub"
        ):
            self.provider.apply(Op("add", Grant("github", "cy", "org", "member")))

        self.assertEqual(self.github.writes(), [])

    def test_a_token_without_read_org_cannot_read(self):
        self.github.scopes = "repo"

        with self.assertRaisesRegex(AccessError, "lacks the read:org scope"):
            self.provider.read()

    def test_the_check_runs_once(self):
        self.provider.read()
        self.provider.read()

        self.assertEqual(
            [c for c in self.github.calls if c[1] == "user"], [("GET", "user", None)]
        )

    def app_provider(self, permissions):
        self.github.scopes = None
        self.github.installations = [
            {"id": 7, "account": {"login": "acme"}, "permissions": permissions}
        ]

        return GitHubProvider("acme", "t", http=self.github, app="ap-app")

    def test_a_github_app_without_members_write_names_the_permission_and_the_links(
        self,
    ):
        self.github.app_owner = {"login": "acme", "type": "Organization"}
        provider = self.app_provider({"members": "read", "administration": "write"})

        self.assertTrue(provider.read())

        with self.assertRaises(AccessError) as raised:
            provider.apply(Op("add", Grant("github", "cy", "org", "member")))

        message = str(raised.exception)
        self.assertIn('Organization → Members "Read and write" (is read)', message)
        self.assertIn(
            "https://github.com/organizations/acme/settings/apps/ap-app/permissions",
            message,
        )
        self.assertIn(
            "https://github.com/organizations/acme/settings/installations/7", message
        )
        self.assertNotIn("Administration", message)

    def test_a_github_app_not_installed_on_the_org_says_where_to_install_it(self):
        provider = self.app_provider({})
        self.github.installations = []

        with self.assertRaisesRegex(
            AccessError, "not installed on acme.*apps/ap-app/installations/new"
        ):
            provider.read()

    def test_a_github_app_with_the_permissions_reads(self):
        provider = self.app_provider({"members": "write", "administration": "write"})

        self.assertIn(Grant("github", "ana", "org", "admin"), provider.read())

    def test_a_github_app_user_token_with_an_empty_scopes_header_reads(self):
        provider = self.app_provider({"members": "write", "administration": "write"})
        self.github.scopes = ""

        self.assertIn(Grant("github", "ana", "org", "admin"), provider.read())

    def test_a_token_without_scopes_header_and_no_app_is_not_checked(self):
        self.github.scopes = None

        self.assertTrue(self.provider.read())
