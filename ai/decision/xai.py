"""
Solar Sentry — Explainable AI (XAI) Module
Agent 8: Cognitive Decision Engine + Explainable AI

Provides transparent explanations, human-readable reason synthesis,
feature attributions, and counterfactuals for observatory decisions.
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Optional
import uuid
from datetime import datetime, timezone

from .types import (
    DecisionType,
    RiskLevel,
    OperationalMode,
    SafetyGate,
    CognitiveInput,
    FactorAttribution,
    Counterfactual,
    DecisionExplanation,
    DecisionTraceStep,
    DecisionTrace,
)


class ExplainableAIEngine:
    """
    Synthesizes human-readable and structured explanations, factor attributions,
    counterfactuals, and audit traces for cognitive decisions.
    """

    @staticmethod
    def synthesize_reasons(
        decision: DecisionType,
        mode: OperationalMode,
        safety_gate: SafetyGate,
        cognitive_input: CognitiveInput,
        weights: Dict[str, float],
        utility: float,
        total_uncertainty: float
    ) -> List[str]:
        """
        Synthesizes a clean, human-readable list of concise reasons explaining WHY.
        Produces strings closely adhering to the specification example:
        e.g., ["environment suitable", "sensor health normal", "image quality acceptable", "future conditions declining"]
        """
        reasons: List[str] = []
        vision = cognitive_input.vision
        env = cognitive_input.environment
        health = cognitive_input.health
        edge = cognitive_input.edge

        # 1. Safety & Critical Gate Reasons
        if safety_gate == SafetyGate.RAIN_ACTIVE or edge.rain_detected:
            reasons.append("safety interlock active: precipitation / rain detected")
        elif safety_gate == SafetyGate.COMMS_TIMEOUT or edge.comms_age_sec > 30.0:
            reasons.append(f"safety interlock active: comms heartbeat lost ({edge.comms_age_sec:.1f}s > 30s)")
        elif safety_gate == SafetyGate.CRITICAL_HARDWARE_FAULT or not health.is_healthy:
            failed_str = ", ".join(health.failed_sensors) if health.failed_sensors else "subsystem fault"
            reasons.append(f"hardware safety trip: critical fault in {failed_str}")

        # 2. Environmental Suitability Reasons
        if env.environment_quality >= 0.85:
            reasons.append("environment optimal")
        elif env.environment_quality >= 0.65:
            reasons.append("environment suitable")
        elif env.environment_quality >= 0.40:
            reasons.append("environment marginal")
        else:
            reasons.append("environment adverse: severe cloud cover / low irradiance")

        # 3. Sensor & Hardware Health Reasons
        if health.overall_health >= 0.90 and not health.failed_sensors and not health.degraded_sensors:
            reasons.append("sensor health normal")
        elif mode == OperationalMode.DEGRADED or health.degraded_sensors:
            degraded_str = ", ".join(health.degraded_sensors or health.failed_sensors)
            reasons.append(f"operating in degraded mode: {degraded_str} uncalibrated/offline")
        elif health.overall_health < 0.60:
            reasons.append("sensor health critically impaired")
        else:
            reasons.append("sensor health degraded")

        # 4. Sensor Agreement / Consistency
        if health.sensor_agreement_score < 0.65:
            reasons.append("conflicting sensor readings detected across telemetry channels")

        # 5. Image & Vision Quality Reasons
        if not vision.solar_disk_detected and env.environment_quality >= 0.60:
            reasons.append("solar disk not acquired in field of view despite adequate sky light")
        elif vision.vision_quality >= 0.85:
            reasons.append("image quality excellent")
        elif vision.vision_quality >= 0.65:
            reasons.append("image quality acceptable")
        elif vision.cloud_coverage > 0.60:
            reasons.append("image quality poor: high cloud occlusion over solar target")
        else:
            reasons.append("image quality degraded / insufficient contrast")

        # 6. Horizon / Predictive Trend Reasons
        if env.rain_probability_30m > 0.40:
            reasons.append(f"high rain risk imminent ({env.rain_probability_30m*100:.0f}% chance in 30m)")
        elif env.prediction_30m < (env.environment_quality - 0.08) or env.solar_irradiance_trend == "DECLINING":
            reasons.append("future conditions declining")
        elif env.prediction_30m > (env.environment_quality + 0.08) or env.solar_irradiance_trend == "RISING":
            reasons.append("future conditions improving")
        else:
            reasons.append("future conditions stable")

        # 7. Uncertainty
        if total_uncertainty > 0.35:
            reasons.append(f"high epistemic uncertainty ({total_uncertainty:.2f}) across perception inputs")

        # Deduplicate while preserving order
        seen = set()
        deduped: List[str] = []
        for r in reasons:
            if r not in seen:
                seen.add(r)
                deduped.append(r)

        return deduped

    @staticmethod
    def compute_feature_attributions(
        cognitive_input: CognitiveInput,
        weights: Dict[str, float]
    ) -> Tuple[List[FactorAttribution], List[FactorAttribution]]:
        """
        Computes additive feature attributions comparing current values to neutral baseline (0.5).
        Returns positive factors (driving toward OBSERVE) and negative factors (inhibiting OBSERVE).
        """
        vision = cognitive_input.vision
        env = cognitive_input.environment
        health = cognitive_input.health

        feature_map = {
            "vision_quality": (vision.vision_quality, weights.get("vision", 0.35)),
            "environment_quality": (env.environment_quality, weights.get("environment", 0.25)),
            "prediction_30m": (env.prediction_30m, weights.get("prediction", 0.25)),
            "overall_health": (health.overall_health, weights.get("health", 0.15)),
            "cloud_clearness": (1.0 - vision.cloud_coverage, weights.get("vision", 0.35) * 0.5),
            "sensor_agreement": (health.sensor_agreement_score, weights.get("health", 0.15) * 0.8),
        }

        positive: List[FactorAttribution] = []
        negative: List[FactorAttribution] = []

        baseline = 0.5
        for feat_name, (val, weight) in feature_map.items():
            impact = weight * (val - baseline)
            if impact >= 0:
                positive.append(FactorAttribution(
                    feature=feat_name,
                    weight=round(weight, 3),
                    value=round(val, 3),
                    impact_score=round(impact, 3),
                    direction="POSITIVE"
                ))
            else:
                negative.append(FactorAttribution(
                    feature=feat_name,
                    weight=round(weight, 3),
                    value=round(val, 3),
                    impact_score=round(impact, 3),
                    direction="NEGATIVE"
                ))

        # Sort by absolute impact descending
        positive.sort(key=lambda x: x.impact_score, reverse=True)
        negative.sort(key=lambda x: x.impact_score)  # most negative first

        return positive, negative

    @staticmethod
    def generate_counterfactuals(
        current_decision: DecisionType,
        safety_gate: SafetyGate,
        cognitive_input: CognitiveInput,
        fused_utility: float,
        observe_threshold: float = 0.70
    ) -> List[Counterfactual]:
        """
        Generates actionable counterfactual statements answering what minimal change
        would transition the system to an alternate decision.
        """
        counterfactuals: List[Counterfactual] = []
        vision = cognitive_input.vision
        env = cognitive_input.environment
        edge = cognitive_input.edge
        health = cognitive_input.health

        # Counterfactual for Safety Gate
        if safety_gate == SafetyGate.RAIN_ACTIVE or edge.rain_detected:
            counterfactuals.append(Counterfactual(
                condition="Rain sensor clears (rain_detected == False)",
                projected_decision=DecisionType.WAIT,
                required_delta="Surface moisture evaporate below analog trigger threshold"
            ))
            return counterfactuals

        if safety_gate == SafetyGate.COMMS_TIMEOUT or edge.comms_age_sec > 30.0:
            counterfactuals.append(Counterfactual(
                condition="Comms telemetry restores (comms_age_sec <= 5.0s)",
                projected_decision=DecisionType.OBSERVE if fused_utility >= observe_threshold else DecisionType.WAIT,
                required_delta=f"Restore network heartbeat within {30.0 - edge.comms_age_sec:.1f}s"
            ))
            return counterfactuals

        # Counterfactual for SCAN
        if current_decision == DecisionType.SCAN:
            counterfactuals.append(Counterfactual(
                condition="Solar disk acquired in image frame (solar_disk_detected == True)",
                projected_decision=DecisionType.OBSERVE,
                required_delta="Pan/tilt servo search sweep locks solar centroid in camera center"
            ))
            return counterfactuals

        # Counterfactual for WAIT -> OBSERVE
        if current_decision == DecisionType.WAIT:
            needed_utility_gain = max(0.01, observe_threshold - fused_utility)
            if vision.vision_quality < 0.65:
                needed_vq = min(1.0, 0.70)
                counterfactuals.append(Counterfactual(
                    condition=f"Vision quality rises to >= {needed_vq:.2f}",
                    projected_decision=DecisionType.OBSERVE,
                    required_delta=f"Vision quality delta of +{needed_vq - vision.vision_quality:.2f} (cloud dissipation)"
                ))
            if env.prediction_30m < 0.65:
                counterfactuals.append(Counterfactual(
                    condition="30-minute weather prediction rises to >= 0.70",
                    projected_decision=DecisionType.OBSERVE,
                    required_delta=f"Forecast improvement of +{0.70 - env.prediction_30m:.2f}"
                ))
            if health.sensor_agreement_score < 0.70:
                counterfactuals.append(Counterfactual(
                    condition="Sensor agreement score reaches >= 0.85",
                    projected_decision=DecisionType.OBSERVE,
                    required_delta="Resolve sensor disagreement between pyranometer/lux and camera"
                ))

        # Counterfactual for OBSERVE -> WAIT
        if current_decision == DecisionType.OBSERVE:
            drop_budget = max(0.05, fused_utility - observe_threshold)
            counterfactuals.append(Counterfactual(
                condition=f"Fused utility drops by {drop_budget:.2f} (e.g. cloud cover increases)",
                projected_decision=DecisionType.WAIT,
                required_delta=f"Cloud coverage increases by +{drop_budget * 1.5:.2f}"
            ))

        return counterfactuals

    @staticmethod
    def build_explanation(
        decision: DecisionType,
        mode: OperationalMode,
        safety_gate: SafetyGate,
        cognitive_input: CognitiveInput,
        weights: Dict[str, float],
        fused_utility: float,
        total_uncertainty: float,
        observe_threshold: float = 0.70
    ) -> DecisionExplanation:
        """Assembles the complete DecisionExplanation model."""
        reasons = ExplainableAIEngine.synthesize_reasons(
            decision=decision,
            mode=mode,
            safety_gate=safety_gate,
            cognitive_input=cognitive_input,
            weights=weights,
            utility=fused_utility,
            total_uncertainty=total_uncertainty
        )

        positive, negative = ExplainableAIEngine.compute_feature_attributions(
            cognitive_input=cognitive_input,
            weights=weights
        )

        counterfactuals = ExplainableAIEngine.generate_counterfactuals(
            current_decision=decision,
            safety_gate=safety_gate,
            cognitive_input=cognitive_input,
            fused_utility=fused_utility,
            observe_threshold=observe_threshold
        )

        primary_reason = reasons[0] if reasons else f"System operating in {decision.value} state"

        uncertainty_summary = (
            f"Consolidated uncertainty is low ({total_uncertainty:.2f})"
            if total_uncertainty <= 0.15
            else f"Consolidated uncertainty is moderate ({total_uncertainty:.2f})"
            if total_uncertainty <= 0.35
            else f"High uncertainty detected ({total_uncertainty:.2f}) - requiring conservative verification"
        )

        return DecisionExplanation(
            primary_reason=primary_reason,
            reasons=reasons,
            positive_factors=positive,
            negative_factors=negative,
            counterfactuals=counterfactuals,
            uncertainty_summary=uncertainty_summary
        )
