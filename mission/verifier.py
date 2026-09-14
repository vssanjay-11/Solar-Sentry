"""Solar Sentry — Closed-Loop Action & Mission Verifier.

Agent 9 Ownership.
Performs closed-loop post-action verification:
- Confirms actuator spatial convergence (target vs actual pan/tilt within tolerance).
- Measures pre-action vs post-action observation quality improvement.
- Assesses criteria satisfaction and issues VerificationResult.
"""

from __future__ import annotations

from typing import Optional
from .types import (
    Command,
    CommandResult,
    VerificationResult,
    VerificationStatus,
    ActionVerb,
)


class ActionVerifier:
    """
    Validates physical convergence and optical/environmental quality progression
    following action execution.
    """

    DEFAULT_ANGLE_TOLERANCE_DEG = 2.0
    DEFAULT_MIN_QUALITY_THRESHOLD = 0.65

    def __init__(
        self,
        angle_tolerance_deg: float = DEFAULT_ANGLE_TOLERANCE_DEG,
        min_quality_threshold: float = DEFAULT_MIN_QUALITY_THRESHOLD,
    ):
        self.angle_tolerance_deg = angle_tolerance_deg
        self.min_quality_threshold = min_quality_threshold

    def verify_action(
        self,
        command: Command,
        result: CommandResult,
        quality_before: float = 0.0,
        quality_after: float = 0.0,
        min_quality_target: Optional[float] = None,
    ) -> VerificationResult:
        """
        Closed-loop verification of executed command.
        Evaluates physical convergence and quality delta.
        """
        target_min = min_quality_target if min_quality_target is not None else self.min_quality_threshold
        delta_q = quality_after - quality_before

        # 1. Command execution status check
        if result.status != "SUCCESS":
            return VerificationResult(
                success=False,
                status=VerificationStatus.FAILED,
                quality_before=quality_before,
                quality_after=quality_after,
                delta_quality=delta_q,
                pan_target=command.pan,
                pan_actual=result.current_pan,
                tilt_target=command.tilt,
                tilt_actual=result.current_tilt,
                converged=False,
                message=f"Action execution failed on edge: {result.status} ({result.message})",
            )

        # 2. Physical convergence check
        converged = True
        convergence_errors = []

        if command.pan is not None:
            err_pan = abs(command.pan - result.current_pan)
            if err_pan > self.angle_tolerance_deg:
                converged = False
                convergence_errors.append(f"Pan error {err_pan:.1f}° > tolerance {self.angle_tolerance_deg}°")

        if command.tilt is not None:
            err_tilt = abs(command.tilt - result.current_tilt)
            if err_tilt > self.angle_tolerance_deg:
                converged = False
                convergence_errors.append(f"Tilt error {err_tilt:.1f}° > tolerance {self.angle_tolerance_deg}°")

        if not converged:
            return VerificationResult(
                success=False,
                status=VerificationStatus.FAILED,
                quality_before=quality_before,
                quality_after=quality_after,
                delta_quality=delta_q,
                pan_target=command.pan,
                pan_actual=result.current_pan,
                tilt_target=command.tilt,
                tilt_actual=result.current_tilt,
                converged=False,
                message=f"Actuator convergence failed: {'; '.join(convergence_errors)}",
            )

        # 3. Safe/Park command verification (only requires physical stowed convergence)
        cmd_verb = command.command.value if isinstance(command.command, ActionVerb) else str(command.command)
        if cmd_verb in ["PARK", "EMERGENCY_STOP"]:
            return VerificationResult(
                success=True,
                status=VerificationStatus.SUCCESS,
                quality_before=quality_before,
                quality_after=quality_after,
                delta_quality=0.0,
                pan_target=command.pan,
                pan_actual=result.current_pan,
                tilt_target=command.tilt,
                tilt_actual=result.current_tilt,
                converged=True,
                message="Park/Safe position verified successfully",
            )

        # 4. Observation quality verification
        # Success if quality improved or is already above target threshold
        if quality_after >= quality_before or quality_after >= target_min:
            return VerificationResult(
                success=True,
                status=VerificationStatus.SUCCESS,
                quality_before=quality_before,
                quality_after=quality_after,
                delta_quality=delta_q,
                pan_target=command.pan,
                pan_actual=result.current_pan,
                tilt_target=command.tilt,
                tilt_actual=result.current_tilt,
                converged=True,
                message=(
                    f"Action verified successfully (quality {quality_before:.2f} -> {quality_after:.2f}, "
                    f"Δ={delta_q:+.2f})"
                ),
            )
        else:
            # Significant unexpected degradation
            return VerificationResult(
                success=False,
                status=VerificationStatus.DEGRADED,
                quality_before=quality_before,
                quality_after=quality_after,
                delta_quality=delta_q,
                pan_target=command.pan,
                pan_actual=result.current_pan,
                tilt_target=command.tilt,
                tilt_actual=result.current_tilt,
                converged=True,
                message=(
                    f"Observation quality degraded below expectations "
                    f"({quality_before:.2f} -> {quality_after:.2f}, Δ={delta_q:+.2f} < target {target_min:.2f})"
                ),
            )
