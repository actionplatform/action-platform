import logging

logging.getLogger("alembic").setLevel(logging.WARNING)

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from action_platform.core.exception import ConfigError

MIGRATIONS = Path(__file__).parent / "migrations"
FIRST_REVISION = "0001"
WEB_MANAGED_TABLE = "user"
log = logging.getLogger("action_platform.db")


def normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]

    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]

    if url.startswith("mysql://"):
        return "mysql+pymysql://" + url[len("mysql://") :]

    return url


class Database:
    def __init__(self, url: str, pool_size: int = 5) -> None:
        if not url:
            raise ConfigError("AP_DATABASE_URL is empty")

        self.url = normalize_url(url)
        self.engine = self._engine(self.url, pool_size)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    @staticmethod
    def _engine(url: str, pool_size: int) -> Engine:
        if url.startswith("sqlite"):
            memory = url in ("sqlite://", "sqlite:///:memory:")
            engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool if memory else None,
            )

            @event.listens_for(engine, "connect")
            def _foreign_keys(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")

            return engine

        return create_engine(url, pool_size=pool_size, pool_pre_ping=True)

    @property
    def dialect(self) -> str:
        return self.engine.dialect.name

    def config(self) -> Config:
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS))
        config.set_main_option("sqlalchemy.url", self.url)
        config.attributes["engine"] = self.engine

        return config

    def current_revision(self) -> str | None:
        with self.engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()

    def head_revision(self) -> str | None:
        return ScriptDirectory.from_config(self.config()).get_current_head()

    def adopted_from_web(self) -> bool:
        return self.current_revision() is None and inspect(self.engine).has_table(
            WEB_MANAGED_TABLE
        )

    def migrate(self) -> str | None:
        config = self.config()

        if self.adopted_from_web():
            command.stamp(config, FIRST_REVISION)

        command.upgrade(config, "head")
        revision = self.current_revision()
        log.info("database %s at revision %s", self.dialect, revision)

        return revision

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self.sessions() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def dispose(self) -> None:
        self.engine.dispose()
