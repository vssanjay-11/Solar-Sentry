"""
Solar Sentry - Database Core & Base Definitions
Provides the declarative base and portable types across PostgreSQL and SQLite.
"""

from datetime import datetime, timezone
import json
from typing import Any
from sqlalchemy import DateTime, TypeDecorator, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Authoritative base class for all Solar Sentry database models."""
    pass


class UTCDateTime(TypeDecorator):
    """
    Timezone-aware UTC DateTime type decorator.
    Ensures datetimes are stored and retrieved consistently as UTC.
    """
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is not None:
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                else:
                    value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is not None and isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
        return value


class PortableJSON(TypeDecorator):
    """
    Portable JSON type decorator.
    Uses native JSONB on PostgreSQL and JSON/Text on SQLite/other dialects.
    Handles serialization/deserialization safely.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value
