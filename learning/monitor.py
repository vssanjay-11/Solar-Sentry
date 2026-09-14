"""
Solar Sentry — Learning Framework: Performance Monitoring & Drift Detection
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Monitors prediction error metrics (MAE, RMSE, bias) and detects covariate
and concept drift using Population Stability Index (PSI) and Kolmogorov-Smirnov tests.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class PerformanceMetrics:
    """Calculated error and accuracy metrics over an evaluation dataset."""
    sample_count: int
    mae_15m: float
    rmse_15m: float
    bias_15m: float  # Mean signed error (positive = overpredicting)
    mae_30m: float
    rmse_30m: float
    bias_30m: float
    decision_alignment_rate: float  # Percentage of predictions that led to optimal decisions


@dataclass
class DriftReport:
    """Audit report for feature and concept drift detection."""
    feature_name: str
    psi_score: float
    ks_statistic: float
    ks_pvalue: float
    is_drift_detected: bool
    severity: str  # "NONE", "MODERATE", "SEVERE"
    recommendation: str


class PerformanceMonitor:
    """Tracks continuous model error and accuracy metrics over rolling time windows."""

    @staticmethod
    def calculate_metrics(samples: List[Any]) -> Optional[PerformanceMetrics]:
        """Calculates MAE, RMSE, and bias across paired prediction samples."""
        paired = [s for s in samples if getattr(s, "actual_quality_15m", None) is not None]
        if not paired:
            return None

        errors_15 = []
        errors_30 = []
        aligned_count = 0

        for s in paired:
            e15 = s.predicted_quality_15m - s.actual_quality_15m
            errors_15.append(e15)

            if s.actual_quality_30m is not None:
                e30 = s.predicted_quality_30m - s.actual_quality_30m
                errors_30.append(e30)

            # Alignment check: if predicted quality >= 0.6 and actual >= 0.5, or both < 0.5
            pred_ok = (s.predicted_quality_15m >= 0.6)
            actual_ok = (s.actual_quality_15m >= 0.5)
            if pred_ok == actual_ok:
                aligned_count += 1

        n = len(errors_15)
        mae15 = float(np.mean(np.abs(errors_15)))
        rmse15 = float(np.sqrt(np.mean(np.square(errors_15))))
        bias15 = float(np.mean(errors_15))

        mae30 = float(np.mean(np.abs(errors_30))) if errors_30 else mae15
        rmse30 = float(np.sqrt(np.mean(np.square(errors_30)))) if errors_30 else rmse15
        bias30 = float(np.mean(errors_30)) if errors_30 else bias15

        return PerformanceMetrics(
            sample_count=n,
            mae_15m=round(mae15, 4),
            rmse_15m=round(rmse15, 4),
            bias_15m=round(bias15, 4),
            mae_30m=round(mae30, 4),
            rmse_30m=round(rmse30, 4),
            bias_30m=round(bias30, 4),
            decision_alignment_rate=round(aligned_count / max(1, n), 4)
        )


class DriftDetector:
    """
    Detects feature distribution shifts between baseline reference data and recent production stream.
    Uses Population Stability Index (PSI) and two-sample Kolmogorov-Smirnov test.
    """

    PSI_WARNING_THRESHOLD = 0.10
    PSI_CRITICAL_THRESHOLD = 0.25

    @staticmethod
    def calculate_psi(baseline: np.ndarray, target: np.ndarray, bins: int = 10) -> float:
        """Calculates Population Stability Index between baseline and target distributions."""
        if len(baseline) < 10 or len(target) < 10:
            return 0.0

        # Create quantile-based bins from baseline
        quantiles = np.linspace(0, 100, bins + 1)
        bin_edges = np.percentile(baseline, quantiles)
        bin_edges[0] -= 1e-5
        bin_edges[-1] += 1e-5

        # Count frequencies
        base_counts, _ = np.histogram(baseline, bins=bin_edges)
        target_counts, _ = np.histogram(target, bins=bin_edges)

        # Convert to proportions with Laplace smoothing
        base_props = (base_counts + 1e-4) / (len(baseline) + 1e-4 * bins)
        target_props = (target_counts + 1e-4) / (len(target) + 1e-4 * bins)

        # PSI formula: sum((target - base) * ln(target / base))
        psi_val = np.sum((target_props - base_props) * np.log(target_props / base_props))
        return float(psi_val)

    @staticmethod
    def detect_drift(
        feature_name: str,
        baseline_values: List[float] | np.ndarray,
        recent_values: List[float] | np.ndarray
    ) -> DriftReport:
        """Runs PSI and distribution analysis for a specific feature."""
        base_arr = np.asarray(baseline_values, dtype=float)
        rec_arr = np.asarray(recent_values, dtype=float)

        if len(base_arr) < 10 or len(rec_arr) < 10:
            return DriftReport(
                feature_name=feature_name,
                psi_score=0.0,
                ks_statistic=0.0,
                ks_pvalue=1.0,
                is_drift_detected=False,
                severity="NONE",
                recommendation="Insufficient samples for statistical drift test"
            )

        psi = DriftDetector.calculate_psi(base_arr, rec_arr)

        # Simple Kolmogorov-Smirnov test via SciPy if available, else empirical CDF max distance
        try:
            from scipy import stats
            ks_res = stats.ks_2samp(base_arr, rec_arr)
            ks_stat = float(ks_res.statistic)
            ks_p = float(ks_res.pvalue)
        except Exception:
            # Fallback empirical max CDF difference
            all_vals = np.sort(np.concatenate([base_arr, rec_arr]))
            cdf1 = np.searchsorted(np.sort(base_arr), all_vals, side='right') / len(base_arr)
            cdf2 = np.searchsorted(np.sort(rec_arr), all_vals, side='right') / len(rec_arr)
            ks_stat = float(np.max(np.abs(cdf1 - cdf2)))
            ks_p = 0.05 if ks_stat > 0.2 else 0.50

        # Assess severity
        if psi >= DriftDetector.PSI_CRITICAL_THRESHOLD or (ks_stat > 0.3 and ks_p < 0.01):
            severity = "SEVERE"
            is_drift = True
            rec = f"Significant drift detected in {feature_name} (PSI={psi:.3f}). Model retraining advised."
        elif psi >= DriftDetector.PSI_WARNING_THRESHOLD:
            severity = "MODERATE"
            is_drift = True
            rec = f"Moderate distribution shift in {feature_name} (PSI={psi:.3f}). Monitor closely."
        else:
            severity = "NONE"
            is_drift = False
            rec = f"Distribution stable (PSI={psi:.3f})."

        return DriftReport(
            feature_name=feature_name,
            psi_score=round(psi, 4),
            ks_statistic=round(ks_stat, 4),
            ks_pvalue=round(ks_p, 4),
            is_drift_detected=is_drift,
            severity=severity,
            recommendation=rec
        )
