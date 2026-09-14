"""
Solar Sentry - Migration Runner
Applies deterministic SQL migrations and tracks schema version history.
"""

from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy import text, Engine

from backend.database.config import get_engine

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "versions"


def get_migration_files() -> List[Path]:
    """Returns sorted list of .sql migration files in the versions directory."""
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda p: p.name)


def init_migration_table(engine: Engine) -> None:
    """Ensures the schema_migrations tracking table exists."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version VARCHAR(64) PRIMARY KEY,
        name VARCHAR(256) NOT NULL,
        applied_at TIMESTAMP WITH TIME ZONE NOT NULL,
        checksum VARCHAR(64) NOT NULL
    );
    """
    with engine.begin() as conn:
        conn.execute(text(create_table_sql))


def get_applied_migrations(engine: Engine) -> Dict[str, Dict[str, Any]]:
    """Returns dictionary of applied migration records keyed by version."""
    init_migration_table(engine)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version, name, applied_at, checksum FROM schema_migrations ORDER BY version"))
        return {
            row[0]: {
                "version": row[0],
                "name": row[1],
                "applied_at": row[2],
                "checksum": row[3],
            }
            for row in result
        }


def compute_checksum(content: str) -> str:
    """Computes SHA-256 checksum of migration script content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def apply_migrations(engine: Engine | None = None) -> List[str]:
    """
    Applies all pending SQL migrations in alphabetical/version order.
    Returns list of newly applied migration names.
    """
    target_engine = engine or get_engine()
    init_migration_table(target_engine)
    applied = get_applied_migrations(target_engine)
    files = get_migration_files()
    newly_applied = []

    for file_path in files:
        version = file_path.name.split("_")[0]
        if version in applied:
            continue

        content = file_path.read_text(encoding="utf-8")
        checksum = compute_checksum(content)

        logger.info(f"Applying migration: {file_path.name}...")

        # Execute statements in the migration file
        with target_engine.begin() as conn:
            # For SQLite / PostgreSQL script execution
            # Split on semicolons while skipping comments/empty lines
            raw_statements = content.split(";")
            for stmt in raw_statements:
                clean_stmt = stmt.strip()
                if clean_stmt:
                    conn.execute(text(clean_stmt))

            # Record migration in tracking table
            conn.execute(
                text(
                    "INSERT INTO schema_migrations (version, name, applied_at, checksum) "
                    "VALUES (:version, :name, :applied_at, :checksum)"
                ),
                {
                    "version": version,
                    "name": file_path.name,
                    "applied_at": datetime.now(timezone.utc),
                    "checksum": checksum,
                },
            )

        newly_applied.append(file_path.name)
        logger.info(f"Successfully applied: {file_path.name}")

    return newly_applied


def get_migration_status(engine: Engine | None = None) -> List[Dict[str, Any]]:
    """Returns status report of all available migrations."""
    target_engine = engine or get_engine()
    applied = get_applied_migrations(target_engine)
    files = get_migration_files()
    status_list = []

    for file_path in files:
        version = file_path.name.split("_")[0]
        is_applied = version in applied
        status_list.append({
            "version": version,
            "filename": file_path.name,
            "status": "APPLIED" if is_applied else "PENDING",
            "applied_at": applied[version]["applied_at"] if is_applied else None,
            "checksum": applied[version]["checksum"] if is_applied else None,
        })

    return status_list


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    applied = apply_migrations()
    print(f"Applied {len(applied)} migrations: {applied}")
    status = get_migration_status()
    for s in status:
        print(f"  [{s['status']}] {s['filename']} (applied: {s['applied_at']})")
