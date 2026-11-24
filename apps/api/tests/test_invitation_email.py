from __future__ import annotations

from datetime import timedelta

from action_platform.core.exception import ProviderError

from app.core.db.models import Invitation
from app.core.shared.clock import now
from tests.test_import_github import ImportCase


class Outbox:
    def __init__(self) -> None:
        self.sent = []
        self.fail = None

    def send(self, mail) -> None:
        if self.fail:
            raise ProviderError(self.fail)

        self.sent.append(mail)


class InvitationEmailTest(ImportCase):
    def setUp(self):
        super().setUp()
        self.outbox = Outbox()

    def invite(self, email="bob@example.com", role="developer"):
        return self.client.post(
            "/api/v1/invitations",
            json={"email": email, "role": role},
            headers=self.h(),
        )

    def resend(self, id):
        return self.client.post(f"/api/v1/invitations/{id}/resend", headers=self.h())

    def listed(self):
        return self.client.get("/api/v1/invitations", headers=self.h()).json()

    def test_without_smtp_nothing_is_sent_and_the_link_stays_the_way(self):
        row = self.invite().json()

        self.assertEqual(row["email_state"], "off")
        self.assertIsNone(row["emailed_at"])
        self.assertEqual(self.listed()[0]["id"], row["id"])

    def test_sends_one_message_whose_link_opens_the_accept_page(self):
        self.app.state.mailer = self.outbox

        row = self.invite().json()

        self.assertEqual(row["email_state"], "sent")
        self.assertIsNotNone(row["emailed_at"])
        self.assertEqual(len(self.outbox.sent), 1)
        mail = self.outbox.sent[0]
        link = f"https://ap.example.com/invite/{row['id']}"
        self.assertEqual(mail.to, "bob@example.com")
        self.assertIn("Acme", mail.subject)
        self.assertIn("Ana", mail.text)
        self.assertIn("developer", mail.text)
        self.assertIn("UTC", mail.text)
        self.assertIn(link, mail.text)
        self.assertIn(link, mail.html)
        self.assertNotIn("Google", mail.text)

    def test_the_mail_mentions_google_when_it_is_configured(self):
        self.app.state.mailer = self.outbox
        self.app.state.google = object()

        self.invite()

        self.assertIn("Google", self.outbox.sent[0].text)

    def test_asking_again_does_not_send_again(self):
        self.app.state.mailer = self.outbox

        first = self.invite().json()
        second = self.invite().json()

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.outbox.sent), 1)

    def test_a_failed_send_keeps_the_invitation_and_says_why(self):
        self.outbox.fail = "cannot send email through smtp.example.com: 535 bad login"
        self.app.state.mailer = self.outbox

        res = self.invite()

        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["email_state"], "failed")
        self.assertIn("535 bad login", res.json()["email_error"])
        self.assertEqual(self.listed()[0]["email_state"], "failed")

    def test_resend_keeps_the_id_renews_the_expiry_and_clears_the_error(self):
        self.outbox.fail = "smtp down"
        self.app.state.mailer = self.outbox
        row = self.invite().json()
        with self.app.state.db.session() as s:
            s.get(Invitation, row["id"]).expires_at = now() + timedelta(hours=1)
        self.outbox.fail = None

        res = self.resend(row["id"])

        self.assertEqual(res.status_code, 200, res.text)
        again = res.json()
        self.assertEqual(again["id"], row["id"])
        self.assertEqual(again["email_state"], "sent")
        self.assertIsNone(again["email_error"])
        with self.app.state.db.session() as s:
            expires = s.get(Invitation, row["id"]).expires_at
        self.assertGreater(expires, now() + timedelta(days=6))
        self.assertEqual(len(self.outbox.sent), 1)
        self.assertEqual(len(self.listed()), 1)

    def test_a_failed_resend_is_recorded_not_raised(self):
        self.app.state.mailer = self.outbox
        row = self.invite().json()
        self.outbox.fail = "smtp down"

        res = self.resend(row["id"])

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["email_state"], "failed")

    def test_resend_needs_a_mailer_and_a_pending_invitation(self):
        row = self.invite().json()

        self.assertEqual(self.resend(row["id"]).status_code, 409)

        self.app.state.mailer = self.outbox
        self.assertEqual(self.resend("nope").status_code, 404)
        self.client.delete(f"/api/v1/invitations/{row['id']}", headers=self.h())
        self.assertEqual(self.resend(row["id"]).status_code, 404)

    def test_a_login_invitation_is_never_emailed(self):
        from app.repositories.organization import OrganizationRepository

        self.app.state.mailer = self.outbox
        with self.app.state.db.session() as s:
            repo = OrganizationRepository(s, self.app.state.sealer)
            login_id = repo.create_login_invitation(
                self.org["id"], self.user_id, "github", "ghost", "developer"
            ).id

        row = next(r for r in self.listed() if r["id"] == login_id)

        self.assertEqual(row["email_state"], "off")
        self.assertEqual(self.resend(login_id).status_code, 409)
        self.assertEqual(self.outbox.sent, [])

    def test_people_invited_by_an_import_get_the_same_email(self):
        from app.services.jobs.worker import Worker
        from app.services.organization import invitation_email

        self.setenv("AP_GITHUB_CLIENT_ID", "cid")
        self.setenv("AP_GITHUB_CLIENT_SECRET", "csecret")
        self.patch(invitation_email, "mailer_from_env", lambda env: self.outbox)

        queued = self.client.post(
            "/api/v1/import/github",
            json={"host_id": "gh", "organization": "acme", "people": ["bob", "ghost"]},
            headers=self.h(),
        )
        self.assertEqual(queued.status_code, 202, queued.text)
        Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)

        self.assertEqual([m.to for m in self.outbox.sent], ["bob@example.com"])
        bob = next(r for r in self.listed() if r["email"] == "bob@example.com")
        self.assertIn(f"/invite/{bob['id']}", self.outbox.sent[0].text)
        self.assertEqual(bob["email_state"], "sent")
