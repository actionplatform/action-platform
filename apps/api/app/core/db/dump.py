import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from sqlalchemy.engine import make_url

from action_platform.core.exception import ActionPlatformError
from app.core.db.database import normalize_url

Run = Callable[..., subprocess.CompletedProcess]

TABLES = "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'"
WIPE = b"DROP SCHEMA public CASCADE;\nCREATE SCHEMA public;\n"
NEWER_SERVER_ONLY = (b"SET transaction_timeout = 0;",)


@dataclass(frozen=True)
class Postgres:
    """pg_dump and psql against one Postgres database, the password handed over in the environment."""

    connection: list[str]
    env: dict[str, str] = field(default_factory=dict)
    run: Run = subprocess.run

    @classmethod
    def from_url(cls, url: str, run: Run = subprocess.run) -> "Postgres":
        parsed = make_url(normalize_url(url))

        if parsed.get_backend_name() != "postgresql":
            raise ActionPlatformError(
                f"db backup and restore need Postgres, not {parsed.get_backend_name()}"
            )

        connection = []

        if parsed.host:
            connection += ["-h", parsed.host]

        if parsed.port:
            connection += ["-p", str(parsed.port)]

        if parsed.username:
            connection += ["-U", parsed.username]

        connection += ["-d", parsed.database or "postgres"]
        env = {}

        if parsed.password:
            env["PGPASSWORD"] = str(parsed.password)

        sslmode = parsed.query.get("sslmode")

        if sslmode:
            env["PGSSLMODE"] = sslmode if isinstance(sslmode, str) else sslmode[-1]

        return cls(connection, env, run)

    def dump_command(self) -> list[str]:
        return ["pg_dump", "--no-owner", "--no-privileges", *self.connection]

    def psql_command(self, *args: str) -> list[str]:
        return ["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", *self.connection, *args]

    def _call(self, command: list[str], **kwargs) -> subprocess.CompletedProcess:
        try:
            result = self.run(command, env={**os.environ, **self.env}, **kwargs)
        except FileNotFoundError as e:
            raise ActionPlatformError(
                f"{command[0]} not found: install the PostgreSQL client"
            ) from e

        if result.returncode != 0:
            raise ActionPlatformError(
                f"{command[0]} exited with {result.returncode}"
                + (f": {result.stderr.decode().strip()}" if result.stderr else "")
            )

        return result

    def backup(self, out: Path | None) -> None:
        """Write a plain SQL dump to `out`, or to stdout when None; a failed dump leaves no file."""
        if out is None:
            self._call(self.dump_command(), stdout=sys.stdout.buffer)
            return

        partial = out.with_name(out.name + ".partial")
        fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)

        try:
            with os.fdopen(fd, "wb") as handle:
                self._call(self.dump_command(), stdout=handle)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise

        partial.replace(out)

    def tables(self) -> int:
        result = self._call(self.psql_command("-tAc", TABLES), capture_output=True)

        return int(result.stdout.decode().strip() or 0)

    def restore(self, dump: bytes, force: bool = False) -> None:
        """Load `dump` in one transaction; a database that already has tables is refused unless `force` drops them first."""
        count = self.tables()

        if count and not force:
            raise ActionPlatformError(
                f"the database already has {count} tables: pass --force to drop them and restore"
            )

        script = (WIPE if count else b"") + b"".join(
            line
            for line in dump.splitlines(keepends=True)
            if line.strip() not in NEWER_SERVER_ONLY
        )
        self._call(
            self.psql_command("--single-transaction"),
            input=script,
            capture_output=True,
        )
