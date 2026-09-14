"""
Solar Sentry - Model Version Repository
Data access operations for AI model metadata, weights tracking, and version provenance.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from backend.database.models.model_version import ModelVersion
from backend.database.repositories.base import BaseRepository


class ModelVersionRepository(BaseRepository[ModelVersion]):
    """Repository managing AI model versions and evaluation metrics."""

    def __init__(self, session: Session):
        super().__init__(ModelVersion, session)

    def register_model(
        self,
        model_id: str,
        subsystem: str,
        name: str,
        version: str,
        weights_path: Optional[str] = None,
        architecture_desc: Optional[str] = None,
        parameters_hash: Optional[str] = None,
        trained_at: Optional[datetime] = None,
        metrics_json: Optional[dict] = None,
        is_active: bool = True,
    ) -> ModelVersion:
        """Registers a new model version or updates existing metadata."""
        model = self.get_by_id(model_id)
        if model is None:
            model = ModelVersion(
                model_id=model_id,
                subsystem=subsystem,
                name=name,
                version=version,
                weights_path=weights_path,
                architecture_desc=architecture_desc,
                parameters_hash=parameters_hash,
                trained_at=trained_at,
                metrics_json=metrics_json,
                is_active=is_active,
                created_at=datetime.now(timezone.utc),
            )
            self.create(model)
        else:
            model.subsystem = subsystem
            model.name = name
            model.version = version
            if weights_path:
                model.weights_path = weights_path
            if architecture_desc:
                model.architecture_desc = architecture_desc
            if parameters_hash:
                model.parameters_hash = parameters_hash
            if trained_at:
                model.trained_at = trained_at
            if metrics_json:
                model.metrics_json = metrics_json
            model.is_active = is_active
            self.update(model)
        return model

    def get_active_model(self, subsystem: str, name: str) -> Optional[ModelVersion]:
        """Returns the currently active model version for a given subsystem and model name."""
        stmt = (
            select(ModelVersion)
            .where(
                and_(
                    ModelVersion.subsystem == subsystem,
                    ModelVersion.name == name,
                    ModelVersion.is_active.is_(True),
                )
            )
            .order_by(ModelVersion.created_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_by_subsystem(self, subsystem: str) -> List[ModelVersion]:
        """Returns all versions registered under a subsystem (e.g. VISION, ANOMALY)."""
        stmt = (
            select(ModelVersion)
            .where(ModelVersion.subsystem == subsystem)
            .order_by(ModelVersion.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def set_active_version(self, model_id: str) -> Optional[ModelVersion]:
        """Sets target model as active and deactivates other versions with the same name."""
        target = self.get_by_id(model_id)
        if target:
            # Deactivate peers
            stmt = (
                select(ModelVersion)
                .where(
                    and_(
                        ModelVersion.subsystem == target.subsystem,
                        ModelVersion.name == target.name,
                        ModelVersion.model_id != model_id,
                    )
                )
            )
            peers = list(self.session.scalars(stmt).all())
            for peer in peers:
                peer.is_active = False
            target.is_active = True
            self.session.flush()
        return target
