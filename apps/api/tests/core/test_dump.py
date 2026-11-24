"""app.core.db.dump — pg_dump and psql commands, the refusal to restore over data, no real Postgres."""

from __future__ import annotations

import subprocess
import unittest

from action_platform.core.exception import ActionPlatformError
from action_platform.testing.fixtures import TempCase

from app.core.db.dump import Postgres

URL = (
    "postgres://action_platform:s3cret@db.internal:6432/action_platform?sslmode=require"
)


class Recorder:
    def __init__(self, *outputs: tuple[int, bytes]) -> None:
        self.outputs = list(outputs)
        self.calls: list[tuple[list[str], dict]] = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        code, stdout = self.outputs.pop(0) if self.outputs else (0, b"")

        if "stdout" in kwargs and hasattr(kwargs["stdout"], "write"):
            kwargs["stdout"].write(stdout)

        return subprocess.CompletedProcess(
            command, code, stdout, b"boom" if code else b""
        )


class FromUrlTest(unittest.TestCase):
    def test_connection_flags_and_the_password_in_the_environment(self):
        postgres = Postgres.from_url(URL)

        self.assertEqual(
            postgres.connection,
            [
                "-h",
                "db.internal",
                "-p",
                "6432",
                "-U",
                "action_platform",
                "-d",
                "action_platform",
            ],
        )
        self.assertEqual(postgres.env, {"PGPASSWORD": "s3cret", "PGSSLMODE": "require"})
        self.assertNotIn("s3cret", " ".join(postgres.dump_command()))
        self.assertEqual(
            postgres.dump_command(),
            ["pg_dump", "--no-owner", "--no-privileges", *postgres.connection],
        )

    def test_refuses_another_database(self):
        for url in ("sqlite:///x.db", "mysql://u:p@h/db"):
            with self.assertRaises(ActionPlatformError):
                Postgres.from_url(url)


class BackupTest(TempCase):
    def test_writes_the_dump_to_a_private_file(self):
        run = Recorder((0, b"CREATE TABLE t ();\n"))
        out = self.tmp_path / "dump.sql"

        Postgres.from_url(URL, run).backup(out)

        command, kwargs = run.calls[0]
        self.assertEqual(command[0], "pg_dump")
        self.assertEqual(kwargs["env"]["PGPASSWORD"], "s3cret")
        self.assertEqual(out.read_bytes(), b"CREATE TABLE t ();\n")
        self.assertEqual(out.stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.tmp_path / "dump.sql.partial").exists())

    def test_a_failed_dump_leaves_no_file(self):
        out = self.tmp_path / "dump.sql"

        with self.assertRaises(ActionPlatformError) as caught:
            Postgres.from_url(URL, Recorder((1, b"half"))).backup(out)

        self.assertIn("pg_dump exited with 1", str(caught.exception))
        self.assertEqual(list(self.tmp_path.iterdir()), [])

    def test_a_missing_client_is_explained(self):
        def missing(command, **kwargs):
            raise FileNotFoundError(command[0])

        with self.assertRaises(ActionPlatformError) as caught:
            Postgres.from_url(URL, missing).backup(self.tmp_path / "dump.sql")

        self.assertIn("pg_dump not found", str(caught.exception))


class RestoreTest(unittest.TestCase):
    DUMP = b"SET statement_timeout = 0;\nSET transaction_timeout = 0;\nCREATE TABLE t ();\n"

    def test_restores_into_an_empty_database_in_one_transaction(self):
        run = Recorder((0, b"0\n"), (0, b""))

        Postgres.from_url(URL, run).restore(self.DUMP)

        (count, _), (load, kwargs) = run.calls
        self.assertEqual(
            count[-2:],
            ["-tAc", "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'"],
        )
        self.assertEqual(load[0], "psql")
        self.assertIn("ON_ERROR_STOP=1", load)
        self.assertIn("--single-transaction", load)
        self.assertEqual(
            kwargs["input"], b"SET statement_timeout = 0;\nCREATE TABLE t ();\n"
        )

    def test_refuses_a_database_with_tables(self):
        run = Recorder((0, b"42\n"))

        with self.assertRaises(ActionPlatformError) as caught:
            Postgres.from_url(URL, run).restore(self.DUMP)

        self.assertIn("already has 42 tables", str(caught.exception))
        self.assertEqual(len(run.calls), 1)

    def test_force_drops_the_tables_in_the_same_transaction(self):
        run = Recorder((0, b"42\n"), (0, b""))

        Postgres.from_url(URL, run).restore(self.DUMP, force=True)

        script = run.calls[1][1]["input"]
        self.assertTrue(
            script.startswith(b"DROP SCHEMA public CASCADE;\nCREATE SCHEMA public;\n")
        )
        self.assertTrue(script.endswith(b"CREATE TABLE t ();\n"))

    def test_a_failed_load_reports_psql(self):
        run = Recorder((0, b"0\n"), (3, b""))

        with self.assertRaises(ActionPlatformError) as caught:
            Postgres.from_url(URL, run).restore(self.DUMP)

        self.assertIn("psql exited with 3: boom", str(caught.exception))
