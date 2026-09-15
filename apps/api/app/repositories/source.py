"""Where this process opens its registry: the one database `build()` (or the worker) configured."""

from functools import lru_cache

from app.repositories.drafts import DraftStore
from app.repositories.registry import DbStore, Registry
from action_platform.core.exception import ConfigError


class RegistrySource:
    database = None

    def configure(self, database) -> Registry:
        self.database = database
        get_registry.cache_clear()
        registry = get_registry()
        registry.adopt_file()

        return registry

    def open(self) -> Registry:
        if self.database is None:
            raise ConfigError("the registry needs a database: set AP_DATABASE_URL")

        return Registry(DbStore(self.database), DraftStore(self.database))


source = RegistrySource()


def configure_registry(database) -> Registry:
    return source.configure(database)


@lru_cache
def get_registry() -> Registry:
    return source.open()
