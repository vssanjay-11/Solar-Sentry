"""
Solar Sentry - Database Configuration & Session Management
Supports both PostgreSQL (production) and SQLite (development/testing) transparently.
"""

from contextlib import contextmanager
import os
from typing import Generator
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool, NullPool

from backend.database.core import Base


class DatabaseConfig:
    """Database configuration options with environment variable overrides."""

    def __init__(
        self,
        url: str | None = None,
        echo: bool = False,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
    ):
        self.url = (
            url
            or os.getenv("SOLAR_SENTRY_DB_URL")
            or os.getenv("DATABASE_URL")
            or "sqlite:///solarsentry.db"
        )
        self.echo = echo or os.getenv("SOLAR_SENTRY_DB_ECHO", "false").lower() in ("true", "1")
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle

    @property
    def is_sqlite(self) -> bool:
        return self.url.startswith("sqlite")

    @property
    def is_memory(self) -> bool:
        return self.url in ("sqlite://", "sqlite:///:memory:", "sqlite:///")


def create_db_engine(config: DatabaseConfig | None = None) -> Engine:
    """Creates a SQLAlchemy engine configured for the selected database dialect."""
    if config is None:
        config = DatabaseConfig()

    engine_kwargs: dict = {
        "echo": config.echo,
    }

    if config.is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if config.is_memory:
            engine_kwargs["poolclass"] = StaticPool
        else:
            engine_kwargs["poolclass"] = NullPool
    else:
        # PostgreSQL / other production RDBMS
        engine_kwargs["poolclass"] = QueuePool
        engine_kwargs["pool_size"] = config.pool_size
        engine_kwargs["max_overflow"] = config.max_overflow
        engine_kwargs["pool_timeout"] = config.pool_timeout
        engine_kwargs["pool_recycle"] = config.pool_recycle
        engine_kwargs["pool_pre_ping"] = True

    engine = create_engine(config.url, **engine_kwargs)

    # SQLite-specific pragmas: enforce foreign keys and enable WAL mode for concurrency
    if config.is_sqlite:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            if not config.is_memory:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return engine


# Default module-level instances
_default_config = DatabaseConfig()
_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine(config: DatabaseConfig | None = None) -> Engine:
    """Returns or initializes the database engine."""
    global _engine, _default_config
    if config is not None:
        return create_db_engine(config)
    if _engine is None:
        _engine = create_db_engine(_default_config)
    return _engine


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Returns or initializes the sessionmaker."""
    global _SessionFactory
    if engine is not None:
        return sessionmaker(autocommit=False, autoflush=False, bind=engine)
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionFactory


def init_db(engine: Engine | None = None) -> None:
    """Initializes all registered models in the database."""
    # Import all models to ensure they register on Base.metadata
    import backend.database.models  # noqa: F401

    target_engine = engine or get_engine()
    Base.metadata.create_all(bind=target_engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI-compatible database session dependency generator."""
    session_factory = get_session_factory()
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def get_db_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Context manager for standalone transactional database sessions."""
    session_factory = get_session_factory(engine)
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
