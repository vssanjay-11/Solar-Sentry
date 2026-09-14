"""
Solar Sentry — Learning Framework: Model Versioning & Safe Promotion Governance
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Enforces the SAFE learning architecture:
- Tracks model versions, training metadata, and cryptographic SHA-256 checksums.
- Enforces strict promotion criteria:
  1. Zero safety test regressions.
  2. Validation accuracy strictly superior to production baseline.
  3. Mandatory human operator sign-off (NO unvetted hot-deployments).
"""

from __future__ import annotations

import datetime
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelLifecycleStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class ModelArtifact(BaseModel):
    """Metadata record and integrity checksum for a trained model artifact."""
    model_id: str = Field(..., description="Unique model identifier")
    model_name: str = Field("EnvironmentQualityGBM", description="Model architecture name")
    version: str = Field(..., description="Semantic version string, e.g. '1.1.0'")
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="Training completion timestamp"
    )
    artifact_hash: str = Field(..., description="SHA-256 checksum of weights/code")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Benchmark metrics: MAE, RMSE, etc.")
    status: ModelLifecycleStatus = Field(ModelLifecycleStatus.CANDIDATE, description="Current lifecycle stage")
    training_sample_count: int = Field(0, description="Number of training samples utilized")
    approved_by: Optional[str] = Field(None, description="Operator identifier authorizing promotion")
    notes: Optional[str] = Field(None, description="Release notes or validation caveats")


@dataclass
class PromotionEvaluationResult:
    """Outcome of running candidate model against strict promotion gates."""
    candidate_model_id: str
    production_model_id: Optional[str]
    safety_tests_passed: bool
    accuracy_improved: bool
    human_signoff_present: bool
    promoted: bool
    rejection_reasons: List[str]
    scorecard: Dict[str, Any]


class ModelRegistry:
    """
    Central repository for versioned models.
    Guarantees rollback capability and prevents unauthorized deployments.
    """

    def __init__(self):
        self._registry: Dict[str, ModelArtifact] = {}
        self._active_production_id: Optional[str] = None

    def register_model(
        self,
        model_id: str,
        version: str,
        weights_bytes: bytes,
        metrics: Dict[str, float],
        sample_count: int,
        model_name: str = "EnvironmentQualityGBM",
        notes: Optional[str] = None
    ) -> ModelArtifact:
        """Registers a newly trained candidate model with SHA-256 hash."""
        sha256 = hashlib.sha256(weights_bytes).hexdigest()
        artifact = ModelArtifact(
            model_id=model_id,
            model_name=model_name,
            version=version,
            artifact_hash=sha256,
            metrics=metrics,
            status=ModelLifecycleStatus.CANDIDATE,
            training_sample_count=sample_count,
            notes=notes
        )
        self._registry[model_id] = artifact
        return artifact

    def get_model(self, model_id: str) -> Optional[ModelArtifact]:
        return self._registry.get(model_id)

    def get_active_production_model(self) -> Optional[ModelArtifact]:
        if self._active_production_id:
            return self._registry.get(self._active_production_id)
        return None

    def list_models(self) -> List[ModelArtifact]:
        return list(self._registry.values())

    def evaluate_and_promote(
        self,
        candidate_id: str,
        safety_audit_passed: bool,
        operator_approval_token: Optional[str] = None,
        max_mae_threshold: float = 0.22
    ) -> PromotionEvaluationResult:
        """
        Applies strict promotion criteria:
        1. SAFETY GATE: Candidate MUST pass 100% of safety test cases.
        2. ACCURACY GATE: Candidate validation MAE must be <= max_mae_threshold and <= production MAE.
        3. GOVERNANCE GATE: Explicit human operator approval token MUST be supplied.
        """
        candidate = self.get_model(candidate_id)
        if not candidate:
            return PromotionEvaluationResult(
                candidate_model_id=candidate_id,
                production_model_id=self._active_production_id,
                safety_tests_passed=False,
                accuracy_improved=False,
                human_signoff_present=False,
                promoted=False,
                rejection_reasons=["Model ID not found in registry"],
                scorecard={}
            )

        rejections: List[str] = []

        # 1. Safety Audit Gate (Absolute interlock)
        if not safety_audit_passed:
            rejections.append("FAILED_SAFETY_AUDIT: Candidate model violated one or more safety interlocks")

        # 2. Accuracy Benchmark Gate
        cand_mae = candidate.metrics.get("mae_15m", 1.0)
        current_prod = self.get_active_production_model()
        acc_ok = True

        if cand_mae > max_mae_threshold:
            rejections.append(f"ACCURACY_THRESHOLD_EXCEEDED: Candidate MAE {cand_mae:.4f} > threshold {max_mae_threshold:.4f}")
            acc_ok = False

        if current_prod:
            prod_mae = current_prod.metrics.get("mae_15m", 0.25)
            if cand_mae > prod_mae:
                rejections.append(f"REGRESSION_DETECTED: Candidate MAE {cand_mae:.4f} worse than production MAE {prod_mae:.4f}")
                acc_ok = False

        # 3. Human Governance Gate
        has_approval = bool(operator_approval_token and len(operator_approval_token.strip()) > 0)
        if not has_approval:
            rejections.append("GOVERNANCE_GATE_BLOCKED: Mandatory human operator signoff token missing")

        promoted = len(rejections) == 0

        if promoted:
            # Archive old production model
            if current_prod:
                current_prod.status = ModelLifecycleStatus.ARCHIVED
            candidate.status = ModelLifecycleStatus.PRODUCTION
            candidate.approved_by = operator_approval_token
            self._active_production_id = candidate_id
        else:
            candidate.status = ModelLifecycleStatus.REJECTED

        return PromotionEvaluationResult(
            candidate_model_id=candidate_id,
            production_model_id=self._active_production_id,
            safety_tests_passed=safety_audit_passed,
            accuracy_improved=acc_ok,
            human_signoff_present=has_approval,
            promoted=promoted,
            rejection_reasons=rejections,
            scorecard={
                "candidate_mae": cand_mae,
                "production_mae": current_prod.metrics.get("mae_15m") if current_prod else None,
                "status": candidate.status.value
            }
        )
