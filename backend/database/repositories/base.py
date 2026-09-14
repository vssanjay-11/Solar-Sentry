"""
Solar Sentry - Base Repository Pattern
Provides generic CRUD abstractions and session delegation.
"""

from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import Session

from backend.database.core import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository managing persistence operations for a declarative model."""

    def __init__(self, model: Type[ModelType], session: Session):
        self.model = model
        self.session = session

    def get_by_id(self, ident: Any) -> Optional[ModelType]:
        """Fetches a single entity by its primary key."""
        return self.session.get(self.model, ident)

    def create(self, entity: ModelType) -> ModelType:
        """Adds and flushes a new entity."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity: ModelType) -> ModelType:
        """Merges changes and flushes."""
        merged = self.session.merge(entity)
        self.session.flush()
        return merged

    def delete(self, entity: ModelType) -> None:
        """Deletes an entity."""
        self.session.delete(entity)
        self.session.flush()

    def count(self) -> int:
        """Returns total row count for this entity."""
        stmt = select(func.count()).select_from(self.model)
        result = self.session.scalar(stmt)
        return result or 0

    def list_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Returns paginated list of all records."""
        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.session.scalars(stmt).all())
