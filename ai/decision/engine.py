"""
Solar Sentry — Cognitive Decision Engine
Agent 8: Cognitive Decision Engine + Explainable AI (XAI)

Implements multimodal decision fusion, safety-aware hierarchical gating,
confidence calibration, uncertainty handling, degraded-mode decisions,
observatory cognitive state management, and structured mission recommendations.
"""

from __future__ import annotations
import math
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .types import (
    DecisionType,
    RiskLevel,
    OperationalMode,
    SafetyGate,
    CognitiveInput,
    DecisionTraceStep,
    DecisionTrace,
    RecommendedAction,
    CognitiveDecision,
)
from .xai import ExplainableAIEngine


class CognitiveDecisionEngine:
    """
    Autonomous Cognitive Decision Engine for Solar Sentry observatory.
    Fuses vision, environment forecasting, hardware health, and edge telemetry
    under a strict safety hierarchy:
    SAFETY > HEALTH > DATA QUALITY > OBSERVATION QUALITY > MISSION OBJECTIVE
    """

    # Critical thresholds
    OBSERVE_UTILITY_THRESHOLD = 0.68
    WAIT_UTILITY_THRESHOLD = 0.38
    MAX_SAFE_COMMS_AGE_SEC = 30.0
    MAX_SAFE_AMBIENT_TEMP_C = 60.0
    UNCERTAINTY_THRESHOLD_HIGH = 0.35
    SENSOR_AGREEMENT_MIN = 0.65

    # Non-critical sensors whose failure triggers DEGRADED mode rather than SAFE
    NON_CRITICAL_SENSORS = {"bmp280", "pressure", "humidity", "dht22", "dht22_temp_secondary"}
    CRITICAL_SENSORS = {"rain", "bh1750", "lux", "pan_tilt_servos", "esp32_core"}

    def __init__(self, history_capacity: int = 50):
        self.history_capacity = history_capacity
        self.decision_history: List[CognitiveDecision] = []
        self.current_cognitive_mode: OperationalMode = OperationalMode.NORMAL
        self.consecutive_observations: int = 0

    def evaluate(self, input_data: CognitiveInput | Dict[str, Any]) -> CognitiveDecision:
        """
        Main cognitive evaluation entrypoint.
        Reasons over multimodal inputs and produces a structured, explainable decision.
        """
        if isinstance(input_data, dict):
            cog_input = CognitiveInput.from_flat_dict(input_data)
        else:
            cog_input = input_data

        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        trace_steps: List[DecisionTraceStep] = []
        levels_evaluated: List[str] = []

        vision = cog_input.vision
        env = cog_input.environment
        health = cog_input.health
        edge = cog_input.edge

        # =====================================================================
        # LEVEL 1: SAFETY GATES (Absolute Precedence)
        # =====================================================================
        levels_evaluated.append("SAFETY")
        safety_gate = SafetyGate.NONE
        interlock_triggered = False

        # 1.1 Rain precipitation interlock
        if edge.rain_detected:
            safety_gate = SafetyGate.RAIN_ACTIVE
            interlock_triggered = True
            trace_steps.append(DecisionTraceStep(
                step="safety_rain_check",
                level="SAFETY",
                gate="RAIN_INTERLOCK",
                passed=False,
                details=f"Rain precipitation detected on analog sensor (raw={edge.rain_raw})",
                metric_value=float(edge.rain_raw),
                threshold=3000.0
            ))
        else:
            trace_steps.append(DecisionTraceStep(
                step="safety_rain_check",
                level="SAFETY",
                gate="RAIN_INTERLOCK",
                passed=True,
                details="No rain detected; moisture sensor dry",
                metric_value=float(edge.rain_raw),
                threshold=3000.0
            ))

        # 1.2 Comms timeout watchdog
        if not interlock_triggered:
            if edge.comms_age_sec > self.MAX_SAFE_COMMS_AGE_SEC:
                safety_gate = SafetyGate.COMMS_TIMEOUT
                interlock_triggered = True
                trace_steps.append(DecisionTraceStep(
                    step="safety_comms_watchdog",
                    level="SAFETY",
                    gate="COMMS_HEARTBEAT",
                    passed=False,
                    details=f"Heartbeat age {edge.comms_age_sec:.1f}s exceeded fail-safe threshold {self.MAX_SAFE_COMMS_AGE_SEC}s",
                    metric_value=edge.comms_age_sec,
                    threshold=self.MAX_SAFE_COMMS_AGE_SEC
                ))
            else:
                trace_steps.append(DecisionTraceStep(
                    step="safety_comms_watchdog",
                    level="SAFETY",
                    gate="COMMS_HEARTBEAT",
                    passed=True,
                    details=f"Comms telemetry fresh ({edge.comms_age_sec:.2f}s)",
                    metric_value=edge.comms_age_sec,
                    threshold=self.MAX_SAFE_COMMS_AGE_SEC
                ))

        # 1.3 Thermal safety limit
        if not interlock_triggered:
            if edge.ambient_temp_c > self.MAX_SAFE_AMBIENT_TEMP_C:
                safety_gate = SafetyGate.THERMAL_EXCURSION
                interlock_triggered = True
                trace_steps.append(DecisionTraceStep(
                    step="safety_thermal_check",
                    level="SAFETY",
                    gate="THERMAL_SAFETY",
                    passed=False,
                    details=f"Ambient temp {edge.ambient_temp_c:.1f}°C exceeded safe limit {self.MAX_SAFE_AMBIENT_TEMP_C}°C",
                    metric_value=edge.ambient_temp_c,
                    threshold=self.MAX_SAFE_AMBIENT_TEMP_C
                ))
            else:
                trace_steps.append(DecisionTraceStep(
                    step="safety_thermal_check",
                    level="SAFETY",
                    gate="THERMAL_SAFETY",
                    passed=True,
                    details=f"Thermal conditions within operating limits ({edge.ambient_temp_c:.1f}°C)",
                    metric_value=edge.ambient_temp_c,
                    threshold=self.MAX_SAFE_AMBIENT_TEMP_C
                ))

        if safety_gate == SafetyGate.RAIN_ACTIVE or safety_gate == SafetyGate.THERMAL_EXCURSION:
            return self._build_safety_decision(
                decision_type=DecisionType.SUSPEND,
                risk_level=RiskLevel.CRITICAL,
                safety_gate=safety_gate,
                cog_input=cog_input,
                trace_id=trace_id,
                trace_steps=trace_steps,
                levels_evaluated=levels_evaluated,
                reason_hint="precipitation/thermal hazard"
            )
        elif safety_gate == SafetyGate.COMMS_TIMEOUT:
            return self._build_safety_decision(
                decision_type=DecisionType.SAFE,
                risk_level=RiskLevel.CRITICAL,
                safety_gate=safety_gate,
                cog_input=cog_input,
                trace_id=trace_id,
                trace_steps=trace_steps,
                levels_evaluated=levels_evaluated,
                reason_hint="communication loss fail-safe"
            )

        # =====================================================================
        # LEVEL 2: HARDWARE & SENSOR HEALTH (Health Hierarchy)
        # =====================================================================
        levels_evaluated.append("HEALTH")
        mode = OperationalMode.NORMAL
        critical_fault_detected = False

        # Check for critical sensor failure
        critical_failed = [s for s in health.failed_sensors if s.lower() in self.CRITICAL_SENSORS]
        if critical_failed or health.overall_health < 0.40:
            critical_fault_detected = True
            safety_gate = SafetyGate.CRITICAL_HARDWARE_FAULT
            trace_steps.append(DecisionTraceStep(
                step="health_integrity_check",
                level="HEALTH",
                gate="CRITICAL_HARDWARE",
                passed=False,
                details=f"Critical hardware failure detected: {critical_failed or 'severe overall health impairment'}",
                metric_value=health.overall_health,
                threshold=0.40
            ))
            return self._build_safety_decision(
                decision_type=DecisionType.SAFE,
                risk_level=RiskLevel.CRITICAL,
                safety_gate=safety_gate,
                cog_input=cog_input,
                trace_id=trace_id,
                trace_steps=trace_steps,
                levels_evaluated=levels_evaluated,
                reason_hint="critical hardware fault"
            )
        else:
            trace_steps.append(DecisionTraceStep(
                step="health_integrity_check",
                level="HEALTH",
                gate="CRITICAL_HARDWARE",
                passed=True,
                details="No critical hardware faults detected",
                metric_value=health.overall_health,
                threshold=0.40
            ))

        # Check for non-critical sensor degradation (triggers DEGRADED mode)
        degraded_sensors = list(set(health.degraded_sensors + [s for s in health.failed_sensors if s.lower() not in self.CRITICAL_SENSORS]))
        if degraded_sensors or (health.overall_health < 0.85 and health.overall_health >= 0.40):
            mode = OperationalMode.DEGRADED
            trace_steps.append(DecisionTraceStep(
                step="health_degradation_assessment",
                level="HEALTH",
                gate="DEGRADED_MODE_INTERLOCK",
                passed=True,
                details=f"Non-critical degradation detected: {degraded_sensors or 'minor health drop'}. Entering DEGRADED mode.",
                metric_value=health.overall_health,
                threshold=0.85
            ))
        else:
            trace_steps.append(DecisionTraceStep(
                step="health_degradation_assessment",
                level="HEALTH",
                gate="DEGRADED_MODE_INTERLOCK",
                passed=True,
                details="All sensors fully nominal. Operating in NORMAL mode.",
                metric_value=health.overall_health,
                threshold=0.85
            ))

        # =====================================================================
        # LEVEL 3: DATA INTEGRITY & UNCERTAINTY HANDLING
        # =====================================================================
        levels_evaluated.append("DATA_QUALITY")

        # Modality weight configuration
        weights = {
            "vision": 0.35,
            "environment": 0.25,
            "prediction": 0.25,
            "health": 0.15
        }

        # In degraded mode, adjust weights to lower health reliance
        if mode == OperationalMode.DEGRADED:
            weights["health"] = 0.05
            weights["vision"] = 0.40
            weights["environment"] = 0.30
            weights["prediction"] = 0.25
            total_w = sum(weights.values())
            weights = {k: v / total_w for k, v in weights.items()}

        # Epistemic + aleatoric uncertainty propagation
        var_v = (vision.uncertainty ** 2) * weights["vision"]
        var_e = (env.uncertainty ** 2) * weights["environment"]
        var_p = (env.uncertainty ** 2) * weights["prediction"]
        var_h = (health.uncertainty ** 2) * weights["health"]
        base_uncertainty = math.sqrt(var_v + var_e + var_p + var_h)

        # Discordance penalty from sensor disagreement
        agreement_penalty = max(0.0, 1.0 - health.sensor_agreement_score) * 0.35
        total_uncertainty = min(1.0, base_uncertainty + agreement_penalty)

        sensor_conflict = health.sensor_agreement_score < self.SENSOR_AGREEMENT_MIN
        if sensor_conflict or total_uncertainty > self.UNCERTAINTY_THRESHOLD_HIGH:
            mode = OperationalMode.UNCERTAIN
            trace_steps.append(DecisionTraceStep(
                step="uncertainty_and_agreement_check",
                level="DATA_QUALITY",
                gate="CONSISTENCY_GATE",
                passed=False,
                details=f"High uncertainty ({total_uncertainty:.2f}) or sensor conflict (agreement={health.sensor_agreement_score:.2f})",
                metric_value=total_uncertainty,
                threshold=self.UNCERTAINTY_THRESHOLD_HIGH
            ))
        else:
            trace_steps.append(DecisionTraceStep(
                step="uncertainty_and_agreement_check",
                level="DATA_QUALITY",
                gate="CONSISTENCY_GATE",
                passed=True,
                details=f"Telemetry consistent (agreement={health.sensor_agreement_score:.2f}, uncertainty={total_uncertainty:.2f})",
                metric_value=total_uncertainty,
                threshold=self.UNCERTAINTY_THRESHOLD_HIGH
            ))

        # =====================================================================
        # LEVEL 4: OBSERVATION QUALITY & MULTIMODAL UTILITY FUSION
        # =====================================================================
        levels_evaluated.append("OBSERVATION_QUALITY")

        # Multi-horizon forecast synthesis (weighted 15m and 30m)
        forecast_horizon_score = (env.prediction_15m * 0.45) + (env.prediction_30m * 0.45) + (env.prediction_60m * 0.10)

        # Base fused observation utility
        raw_utility = (
            weights["vision"] * vision.vision_quality +
            weights["environment"] * env.environment_quality +
            weights["prediction"] * forecast_horizon_score +
            weights["health"] * health.overall_health
        )

        # Apply trend dampening or boost
        trend_adjustment = 0.0
        if env.prediction_30m < (env.environment_quality - 0.08) or env.solar_irradiance_trend == "DECLINING":
            # Future conditions declining: observation utility slightly penalised for sustained runs,
            # but immediate opportunity windows must be harvested with alert
            trend_adjustment -= 0.02
        elif env.prediction_30m > (env.environment_quality + 0.08) or env.solar_irradiance_trend == "RISING":
            trend_adjustment += 0.02

        # Degradation penalty if in degraded mode
        degradation_penalty = 0.04 if mode == OperationalMode.DEGRADED else 0.0
        fused_utility = max(0.0, min(1.0, raw_utility + trend_adjustment - degradation_penalty))

        trace_steps.append(DecisionTraceStep(
            step="multimodal_utility_fusion",
            level="OBSERVATION_QUALITY",
            gate="UTILITY_SCORING",
            passed=fused_utility >= self.OBSERVE_UTILITY_THRESHOLD,
            details=f"Computed fused utility={fused_utility:.3f} (raw={raw_utility:.3f}, trend={trend_adjustment:+.3f}, degradation={-degradation_penalty:.3f})",
            metric_value=fused_utility,
            threshold=self.OBSERVE_UTILITY_THRESHOLD
        ))

        # =====================================================================
        # LEVEL 5: MISSION OBJECTIVE & ACTION ARBITRATION
        # =====================================================================
        levels_evaluated.append("MISSION_OBJECTIVE")

        # Check for imminent rain within 30 min
        if env.rain_probability_30m >= 0.70:
            decision = DecisionType.SUSPEND
            risk = RiskLevel.HIGH
            rec_action = RecommendedAction(
                action="PREEMPTIVE_PARK",
                suggested_duration_sec=900,
                safe_stow_required=True,
                priority=1,
                guidance="High probability of impending rain within 30 minutes; stow optical payload to prevent wetting"
            )
        # Check if sky is bright/clear but solar disk is NOT detected -> trigger SCAN
        elif (not vision.solar_disk_detected) and env.environment_quality >= 0.60 and edge.lux >= 8000.0:
            decision = DecisionType.SCAN
            risk = RiskLevel.MODERATE
            rec_action = RecommendedAction(
                action="ACTIVE_SOLAR_SEARCH",
                suggested_duration_sec=120,
                safe_stow_required=False,
                priority=2,
                guidance="Solar disk centroid missing from camera view despite suitable ambient daylight; initiate spiral/raster search"
            )
        # Check for high uncertainty mode -> conservative gating
        elif mode == OperationalMode.UNCERTAIN:
            if total_uncertainty > 0.45 or health.sensor_agreement_score < 0.50:
                decision = DecisionType.WAIT
                risk = RiskLevel.HIGH
                rec_action = RecommendedAction(
                    action="VERIFY_TELEMETRY",
                    suggested_duration_sec=60,
                    safe_stow_required=False,
                    priority=3,
                    guidance="Hold tracking pose; sensors in active disagreement. Wait for cross-sensor convergence."
                )
            elif fused_utility >= 0.72:
                # Modest uncertainty but high overall utility: allow observation under cautious monitoring
                decision = DecisionType.OBSERVE
                risk = RiskLevel.MODERATE
                rec_action = RecommendedAction(
                    action="ACQUIRE_SCIENCE_TELEMETRY",
                    suggested_duration_sec=180,
                    safe_stow_required=False,
                    priority=2,
                    guidance="Proceed with guarded observation; frequent calibration checks required"
                )
            else:
                decision = DecisionType.WAIT
                risk = RiskLevel.MODERATE
                rec_action = RecommendedAction(
                    action="HOLD_AND_REASSESS",
                    suggested_duration_sec=120,
                    safe_stow_required=False,
                    priority=3,
                    guidance="Uncertain observation conditions; maintain standby until confidence metrics stabilize"
                )
        # Normal or Degraded mode: evaluate utility thresholds
        elif fused_utility >= self.OBSERVE_UTILITY_THRESHOLD:
            decision = DecisionType.OBSERVE
            risk = RiskLevel.LOW if mode == OperationalMode.NORMAL and env.rain_probability_30m < 0.20 else RiskLevel.MODERATE
            rec_action = RecommendedAction(
                action="ACQUIRE_SCIENCE_TELEMETRY",
                suggested_duration_sec=300 if env.prediction_30m >= 0.70 else 120,
                safe_stow_required=False,
                priority=2,
                guidance="Observation conditions suitable; lock tracking loop and capture solar imagery"
            )
        elif fused_utility >= self.WAIT_UTILITY_THRESHOLD or env.prediction_30m >= 0.65:
            decision = DecisionType.WAIT
            risk = RiskLevel.MODERATE
            rec_action = RecommendedAction(
                action="HOLD_TRACKING_STANDBY",
                suggested_duration_sec=180,
                safe_stow_required=False,
                priority=3,
                guidance="Current sky clarity marginal (possible cloud passage); maintain tracking pose awaiting window"
            )
        else:
            decision = DecisionType.SUSPEND
            risk = RiskLevel.HIGH
            rec_action = RecommendedAction(
                action="STANDBY_STOW",
                suggested_duration_sec=600,
                safe_stow_required=False,
                priority=3,
                guidance="Poor observation quality across all sensor streams with no near-term improvement forecast; suspend operations"
            )

        trace_steps.append(DecisionTraceStep(
            step="arbitrated_decision",
            level="MISSION_OBJECTIVE",
            gate="ACTION_ARBITER",
            passed=True,
            details=f"Selected decision: {decision.value} (Risk: {risk.value}, Mode: {mode.value})",
            metric_value=fused_utility,
            threshold=self.OBSERVE_UTILITY_THRESHOLD
        ))

        # =====================================================================
        # CONFIDENCE CALCULATION
        # =====================================================================
        # Confidence reflects agreement among models, distance from threshold,
        # and inverse uncertainty.
        margin = abs(fused_utility - self.OBSERVE_UTILITY_THRESHOLD)
        margin_score = min(0.35, margin * 1.2)
        base_conf = 0.60 + margin_score + (health.sensor_agreement_score * 0.15) - (total_uncertainty * 0.25)

        if decision == DecisionType.OBSERVE:
            # Boost confidence if conditions are excellent
            if fused_utility >= 0.85 and total_uncertainty <= 0.10:
                base_conf = max(base_conf, 0.94)
            elif fused_utility >= 0.75 and total_uncertainty <= 0.15:
                base_conf = max(base_conf, 0.90)

        # Dampen confidence if degraded or high uncertainty
        if mode == OperationalMode.DEGRADED:
            base_conf *= 0.92
        elif mode == OperationalMode.UNCERTAIN:
            base_conf *= 0.85

        confidence = max(0.20, min(0.98, base_conf))

        # =====================================================================
        # EXPLAINABLE AI SYNTHESIS & AUDIT TRACE
        # =====================================================================
        explanation = ExplainableAIEngine.build_explanation(
            decision=decision,
            mode=mode,
            safety_gate=safety_gate,
            cognitive_input=cog_input,
            weights=weights,
            fused_utility=fused_utility,
            total_uncertainty=total_uncertainty,
            observe_threshold=self.OBSERVE_UTILITY_THRESHOLD
        )

        trace = DecisionTrace(
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            hierarchy_levels_evaluated=levels_evaluated,
            steps=trace_steps,
            gating_interlock=safety_gate,
            fused_utility_score=round(fused_utility, 3),
            total_uncertainty=round(total_uncertainty, 3)
        )

        final_decision = CognitiveDecision(
            decision=decision,
            confidence=round(confidence, 2),
            risk=risk,
            mode=mode,
            reasons=explanation.reasons,
            fused_utility=round(fused_utility, 3),
            total_uncertainty=round(total_uncertainty, 3),
            recommended_action=rec_action,
            explanation=explanation,
            trace=trace,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # Update cognitive memory
        self._update_cognitive_state(final_decision)

        return final_decision

    def _build_safety_decision(
        self,
        decision_type: DecisionType,
        risk_level: RiskLevel,
        safety_gate: SafetyGate,
        cog_input: CognitiveInput,
        trace_id: str,
        trace_steps: List[DecisionTraceStep],
        levels_evaluated: List[str],
        reason_hint: str
    ) -> CognitiveDecision:
        """Constructs an immediate fail-safe decision overriding all operational logic."""
        if decision_type == DecisionType.SUSPEND:
            action_str = "EMERGENCY_PARK"
            guidance = "Hardware safety interlock triggered: immediately park pan/tilt servos and cover optics"
            stow = True
        else:
            action_str = "ENTER_SAFE_MODE"
            guidance = "Observatory entering fail-safe state: system parked awaiting operator or comms restoration"
            stow = True

        rec_action = RecommendedAction(
            action=action_str,
            suggested_duration_sec=0,
            safe_stow_required=stow,
            priority=1,
            guidance=guidance
        )

        weights = {"vision": 0.0, "environment": 0.0, "prediction": 0.0, "health": 1.0}
        explanation = ExplainableAIEngine.build_explanation(
            decision=decision_type,
            mode=OperationalMode.SAFE_MODE,
            safety_gate=safety_gate,
            cognitive_input=cog_input,
            weights=weights,
            fused_utility=0.0,
            total_uncertainty=0.0,
            observe_threshold=self.OBSERVE_UTILITY_THRESHOLD
        )

        trace = DecisionTrace(
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            hierarchy_levels_evaluated=levels_evaluated,
            steps=trace_steps,
            gating_interlock=safety_gate,
            fused_utility_score=0.0,
            total_uncertainty=0.0
        )

        decision = CognitiveDecision(
            decision=decision_type,
            confidence=0.99,
            risk=risk_level,
            mode=OperationalMode.SAFE_MODE,
            reasons=explanation.reasons,
            fused_utility=0.0,
            total_uncertainty=0.0,
            recommended_action=rec_action,
            explanation=explanation,
            trace=trace,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        self._update_cognitive_state(decision)
        return decision

    def _update_cognitive_state(self, decision: CognitiveDecision) -> None:
        """Maintains cognitive history and state transitions."""
        self.decision_history.append(decision)
        if len(self.decision_history) > self.history_capacity:
            self.decision_history.pop(0)

        self.current_cognitive_mode = decision.mode
        if decision.decision == DecisionType.OBSERVE:
            self.consecutive_observations += 1
        else:
            self.consecutive_observations = 0

    def reset_state(self) -> None:
        """Resets engine state and history."""
        self.decision_history.clear()
        self.current_cognitive_mode = OperationalMode.NORMAL
        self.consecutive_observations = 0
