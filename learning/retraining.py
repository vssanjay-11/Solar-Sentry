"""
Solar Sentry — Learning Framework: Offline Retraining Workflow
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Executes controlled, offline retraining of observation quality and environment models.
Operates strictly in an isolated staging sandbox without touching live operations.
"""

from __future__ import annotations

import datetime
import io
import pickle
import uuid
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ai.environment.models.ml_model import GradientBoostingQualityModel
from learning.collector import ExperienceSample
from learning.governance import ModelArtifact, ModelRegistry


class OfflineRetrainingWorkflow:
    """
    Manages offline data preparation, hyperparameter fitting,
    shadow benchmarking, and candidate registration.
    """

    def __init__(self, registry: ModelRegistry):
        self.registry = registry

    def prepare_dataset(
        self,
        samples: List[ExperienceSample],
        val_ratio: float = 0.2
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Converts experience samples into feature matrices and target vectors."""
        paired = [s for s in samples if s.actual_quality_15m is not None]
        if len(paired) < 10:
            raise ValueError(f"Insufficient paired samples for retraining (found {len(paired)}, minimum 10 required)")

        X_rows = []
        y_rows = []
        for s in paired:
            f = s.features
            # Standard feature vector conforming to ai/environment/features.py
            row = [
                f.get("clearness_index", 0.7),
                f.get("cloud_proxy", 0.1),
                f.get("irradiance_volatility", 0.05),
                f.get("humidity", 40.0),
                f.get("pressure_trend", 0.0),
                f.get("solar_elevation_deg", 45.0),
                f.get("condensation_depression_c", 10.0),
            ]
            X_rows.append(row)
            y_rows.append(s.actual_quality_15m)

        X = np.array(X_rows, dtype=np.float32)
        y = np.array(y_rows, dtype=np.float32)

        # Split train / val
        n = len(X)
        indices = np.arange(n)
        np.random.seed(42)
        np.random.shuffle(indices)

        val_size = int(n * val_ratio)
        train_idx = indices[val_size:]
        val_idx = indices[:val_size]

        return X[train_idx], y[train_idx], X[val_idx], y[val_idx]

    def execute_retraining(
        self,
        samples: List[ExperienceSample],
        target_version: str,
        notes: Optional[str] = None
    ) -> ModelArtifact:
        """
        Fits a candidate GradientBoostingQualityModel, computes validation metrics,
        and registers the model as a CANDIDATE in the ModelRegistry.
        """
        X_train, y_train, X_val, y_val = self.prepare_dataset(samples)

        # Train model
        model = GradientBoostingQualityModel(version=target_version)
        # GradientBoostingRegressor fits 1D targets
        model.model.fit(X_train, y_train)
        model.is_fitted = True

        # Evaluate on validation split
        preds = model.model.predict(X_val)
        mae = float(np.mean(np.abs(preds - y_val)))
        rmse = float(np.sqrt(np.mean(np.square(preds - y_val))))

        metrics = {
            "mae_15m": round(mae, 4),
            "rmse_15m": round(rmse, 4),
            "train_samples": len(X_train),
            "val_samples": len(X_val)
        }

        # Serialize weights to bytes
        buffer = io.BytesIO()
        pickle.dump(model.model, buffer)
        weights_bytes = buffer.getvalue()

        model_id = f"model-{target_version}-{uuid.uuid4().hex[:6]}"
        artifact = self.registry.register_model(
            model_id=model_id,
            version=target_version,
            weights_bytes=weights_bytes,
            metrics=metrics,
            sample_count=len(samples),
            notes=notes
        )
        return artifact
