from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


class Database:
    """Owns the SQLAlchemy engine and short-lived transactional sessions."""

    def __init__(self, url: str, *, pool_size: int = 5, max_overflow: int = 10) -> None:
        options: dict[str, object] = {"pool_pre_ping": True}
        if not url.startswith("sqlite"):
            options.update(pool_size=pool_size, max_overflow=max_overflow)
        self.engine: Engine = create_engine(url, **options)
        self._sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Iterator[Session]:
        value = self._sessions()
        try:
            yield value
            value.commit()
        except Exception:
            value.rollback()
            raise
        finally:
            value.close()


@lru_cache
def get_database() -> Database:
    settings = get_settings()
    return Database(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
