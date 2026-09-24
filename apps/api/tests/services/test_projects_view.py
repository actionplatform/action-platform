"""app.services.projects.view — the rows the projects listing returns."""

import unittest
from datetime import datetime
from types import SimpleNamespace

from app.services.projects.view import ProjectView

EARLY = datetime(2026, 1, 1)
LATER = datetime(2026, 2, 1)
LATEST = datetime(2026, 3, 1)


class FakeDirectory:
    def __init__(self):
        self.projects = {
            "o1": [
                SimpleNamespace(
                    id="p1",
                    name="One",
                    slug="one",
                    description="",
                    team_id="t1",
                    created_at=EARLY,
                ),
                SimpleNamespace(
                    id="p2",
                    name="Two",
                    slug="two",
                    description="d",
                    team_id=None,
                    created_at=LATER,
                ),
            ],
            "o2": [
                SimpleNamespace(
                    id="p3",
                    name="Three",
                    slug="three",
                    description="",
                    team_id=None,
                    created_at=EARLY,
                )
            ],
        }
        self.apps = {
            "p1": [
                SimpleNamespace(
                    id="a1",
                    name="api",
                    registry_id="r1",
                    source_host_id="h1",
                    created_at=LATER,
                    last_synced_at=LATEST,
                )
            ]
        }
        self.calls = []

    def projects_of(self, org_id, project_id):
        self.calls.append(("projects_of", org_id, project_id))
        return self.projects.get(org_id, [])

    def team(self, org_id, team_id):
        return SimpleNamespace(id=team_id, name="Core")

    def apps_of(self, project_id, app_id):
        self.calls.append(("apps_of", project_id, app_id))
        return self.apps.get(project_id, [])


class FakeQueue:
    def projects_being_destroyed(self, organization_id):
        return {"p2"} if organization_id == "o1" else set()


def caller(*orgs, project_id=None, app_id=None):
    return SimpleNamespace(
        organizations=[(o, "owner") for o in orgs],
        project_id=project_id,
        app_id=app_id,
    )


class ProjectViewTest(unittest.TestCase):
    def setUp(self):
        self.directory = FakeDirectory()
        self.view = ProjectView(self.directory, FakeQueue())
        self.o1 = SimpleNamespace(id="o1", name="Acme")
        self.o2 = SimpleNamespace(id="o2", name="Beta")

    def test_rows_join_team_and_apps(self):
        first, second = self.view.rows(caller(self.o1), self.o1)

        self.assertEqual(first.team.name, "Core")
        self.assertEqual([a.id for a in first.apps], ["a1"])
        self.assertEqual(first.apps[0].registry_id, "r1")
        self.assertIsNone(first.organization)
        self.assertIsNone(second.team)
        self.assertEqual(second.apps, [])

    def test_updated_at_is_the_latest_moment(self):
        first, second = self.view.rows(caller(self.o1), self.o1)

        self.assertEqual(first.updated_at, LATEST)
        self.assertEqual(second.updated_at, LATER)

    def test_tearing_down_follows_the_queue(self):
        first, second = self.view.rows(caller(self.o1), self.o1)

        self.assertFalse(first.tearing_down)
        self.assertTrue(second.tearing_down)

    def test_rows_honour_the_token_scope(self):
        self.view.rows(caller(self.o1, project_id="p1", app_id="a1"), self.o1)

        self.assertIn(("projects_of", "o1", "p1"), self.directory.calls)
        self.assertIn(("apps_of", "p1", "a1"), self.directory.calls)

    def test_across_tags_every_organization(self):
        rows = self.view.across(caller(self.o1, self.o2))

        self.assertEqual([r.id for r in rows], ["p1", "p2", "p3"])
        self.assertEqual([r.organization.name for r in rows], ["Acme", "Acme", "Beta"])
