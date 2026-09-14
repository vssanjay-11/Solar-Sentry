"""
Unit tests for Solar Sentry database configuration, engine creation, and session management.
"""

import unittest
from sqlalchemy import text
from backend.database.config import DatabaseConfig, create_db_engine, get_db, get_db_session, init_db
from backend.database.core import Base


class TestDatabaseConfig(unittest.TestCase):
    """Validates configuration parameters and engine behaviors."""

    def test_default_config(self):
        cfg = DatabaseConfig()
        self.assertTrue(cfg.is_sqlite)
        self.assertFalse(cfg.is_memory)
        self.assertEqual(cfg.pool_size, 10)

    def test_memory_config(self):
        cfg = DatabaseConfig(url="sqlite:///:memory:")
        self.assertTrue(cfg.is_sqlite)
        self.assertTrue(cfg.is_memory)

    def test_engine_creation_and_pragmas(self):
        cfg = DatabaseConfig(url="sqlite:///:memory:")
        engine = create_db_engine(cfg)
        with engine.connect() as conn:
            # Check foreign keys enabled
            result = conn.execute(text("PRAGMA foreign_keys")).scalar()
            self.assertEqual(result, 1)

    def test_get_db_session_context(self):
        cfg = DatabaseConfig(url="sqlite:///:memory:")
        engine = create_db_engine(cfg)
        init_db(engine)

        with get_db_session(engine) as session:
            result = session.execute(text("SELECT 1")).scalar()
            self.assertEqual(result, 1)

    def test_get_db_generator(self):
        cfg = DatabaseConfig(url="sqlite:///:memory:")
        engine = create_db_engine(cfg)
        from backend.database.config import get_session_factory
        factory = get_session_factory(engine)
        session = factory()
        try:
            val = session.execute(text("SELECT 42")).scalar()
            self.assertEqual(val, 42)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
