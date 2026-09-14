"""
Unit tests for Solar Sentry database migration runner and DDL schema scripts.
"""

import unittest
from sqlalchemy import text
from backend.database.config import DatabaseConfig, create_db_engine
from backend.database.migrations.runner import (
    apply_migrations,
    get_migration_status,
    get_applied_migrations,
)


class TestMigrations(unittest.TestCase):
    """Validates pure SQL migration execution, tracking, and idempotency."""

    def setUp(self):
        self.engine = create_db_engine(DatabaseConfig(url="sqlite:///:memory:"))

    def test_migration_execution_and_tracking(self):
        applied = apply_migrations(self.engine)
        self.assertIn("001_initial_schema.sql", applied)

        # Verify tracking table
        applied_dict = get_applied_migrations(self.engine)
        self.assertIn("001", applied_dict)
        self.assertEqual(applied_dict["001"]["name"], "001_initial_schema.sql")

        # Verify status
        status = get_migration_status(self.engine)
        self.assertEqual(len(status), 1)
        self.assertEqual(status[0]["status"], "APPLIED")

        # Verify tables exist in DB
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            ).fetchall()
            table_names = [r[0] for r in result]
            self.assertIn("devices", table_names)
            self.assertIn("telemetry_records", table_names)
            self.assertIn("observations", table_names)
            self.assertIn("commands", table_names)
            self.assertIn("schema_migrations", table_names)

    def test_migration_idempotency(self):
        # Run first time
        apply_migrations(self.engine)
        # Run second time
        second_run = apply_migrations(self.engine)
        self.assertEqual(len(second_run), 0)


if __name__ == "__main__":
    unittest.main()
