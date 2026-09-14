"""Solar Sentry — Mission Execution Engine.

Agent 9 Ownership.
Executes planned missions step-by-step:
- Action sequencing and dispatch
- Watchdog timeouts
- Closed-loop verification
- Retry policies
- Failure handling and immediate safety aborts
- Mission result generation
"""

from __future__ import annotations

import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from .types import (
    Mission,
    MissionState,
    MissionResult,
    MissionAction,
    ActionStatus,
    VerificationStatus,
    FailureReason,
)
from .dispatcher import CommandDispatcherInterface
from .verifier import ActionVerifier
from .recovery import SafeRecoveryManager

logger = logging.getLogger("MissionExecutor")


class MissionExecutor:
    """
    Executes a Mission through ordered actions, verifying outcomes,
    monitoring timeouts, retrying transient glitches, and aborting on safety trips.
    """

    def __init__(
        self,
        dispatcher: CommandDispatcherInterface,
        verifier: Optional[ActionVerifier] = None,
        recovery_manager: Optional[SafeRecoveryManager] = None,
    ):
        self.dispatcher = dispatcher
        self.verifier = verifier or ActionVerifier()
        self.recovery_manager = recovery_manager or SafeRecoveryManager(dispatcher)

    def execute_mission(
        self,
        mission: Mission,
        quality_before: float = 0.71,
        quality_after: float = 0.86,
        safety_interlock_active: bool = False,
    ) -> MissionResult:
        """
        Executes a planned mission end-to-end.
        """
        mission.status = MissionState.EXECUTING
        mission.started_at = datetime.now(timezone.utc).isoformat()
        t_start = time.time()
        mission.log(f"Starting execution of mission {mission.mission_id} ({mission.name})")

        # 1. Pre-execution Safety Interlock Check
        if safety_interlock_active:
            mission.status = MissionState.ABORTED
            mission.log("Mission aborted pre-execution: Local safety interlock active")
            self.recovery_manager.execute_emergency_suspension(
                reason="Pre-flight safety interlock trip",
                trip_type=FailureReason.SAFETY_INTERLOCK,
            )
            return self._finalize_result(
                mission=mission,
                t_start=t_start,
                failure_reason="Safety interlock active prior to execution",
                safe_recovery=True,
            )

        commands_dispatched: List[Dict[str, Any]] = []
        command_results: List[Dict[str, Any]] = []
        last_verification = None
        has_failure = False
        failure_msg = None

        # 2. Sequential Action Execution Loop
        for action in mission.actions:
            action.status = ActionStatus.IN_PROGRESS
            action.start_time = time.time()
            mission.log(f"Executing action {action.action_id} ({action.action_type})")

            # Retry loop for this action
            attempt = 0
            action_success = False

            while attempt <= action.max_retries and not action_success:
                attempt += 1
                action.retry_count = attempt - 1
                if attempt > 1:
                    mission.log(f"Retry attempt {attempt - 1}/{action.max_retries} for action {action.action_id}")

                # Dispatch command with timeout
                cmd_dict = action.command.to_dict()
                commands_dispatched.append(cmd_dict)

                res = self.dispatcher.dispatch(action.command, timeout_sec=action.timeout_sec)
                action.result = res
                command_results.append(res.to_dict())

                # Check for Safety Rejection from Edge
                if res.status == "REJECTED_SAFETY":
                    mission.status = MissionState.ABORTED
                    action.status = ActionStatus.FAILED
                    action.error_message = f"Command rejected by edge safety interlock: {res.message}"
                    mission.log(f"[SAFETY OVERRIDE] {action.error_message}. Aborting mission.")
                    self.recovery_manager.execute_emergency_suspension(
                        reason=res.message,
                        trip_type=FailureReason.RAIN_OVERRIDE if "rain" in res.message.lower() else FailureReason.SAFETY_INTERLOCK,
                    )
                    return self._finalize_result(
                        mission=mission,
                        t_start=t_start,
                        commands_dispatched=commands_dispatched,
                        command_results=command_results,
                        failure_reason=action.error_message,
                        safe_recovery=True,
                    )

                # Check for Timeout
                if "timed out" in res.message.lower():
                    action.status = ActionStatus.TIMED_OUT
                    action.error_message = res.message
                    mission.log(f"Action {action.action_id} timed out on attempt {attempt}")
                    continue

                # Check for Execution Error
                if res.status != "SUCCESS":
                    action.status = ActionStatus.FAILED
                    action.error_message = res.message
                    mission.log(f"Action {action.action_id} failed on attempt {attempt}: {res.message}")
                    continue

                # Action succeeded on edge, proceed to verification
                action_success = True

            action.end_time = time.time()

            if not action_success:
                has_failure = True
                failure_msg = action.error_message or "Action failed after exhausting retries"
                mission.log(f"Action {action.action_id} permanently failed: {failure_msg}")
                break

            # 3. Closed-Loop Verification
            mission.status = MissionState.VERIFYING
            target_min_q = mission.objective.target_quality_min
            ver_res = self.verifier.verify_action(
                command=action.command,
                result=action.result,
                quality_before=quality_before,
                quality_after=quality_after,
                min_quality_target=target_min_q,
            )
            action.verification = ver_res
            last_verification = ver_res

            if ver_res.success:
                action.status = ActionStatus.COMPLETED
                mission.log(f"Action {action.action_id} verified SUCCESS: {ver_res.message}")
            else:
                action.status = ActionStatus.FAILED
                has_failure = True
                failure_msg = f"Verification failed: {ver_res.message}"
                mission.log(f"Action {action.action_id} verification FAILED: {ver_res.message}")
                break

        # 4. Mission Completion & Outcome Determination
        if has_failure:
            mission.status = MissionState.FAILED
            mission.log(f"Mission failed: {failure_msg}")
        else:
            mission.status = MissionState.COMPLETED
            mission.log(f"Mission {mission.mission_id} completed successfully.")

        return self._finalize_result(
            mission=mission,
            t_start=t_start,
            commands_dispatched=commands_dispatched,
            command_results=command_results,
            last_verification=last_verification,
            failure_reason=failure_msg,
            safe_recovery=False,
        )

    def _finalize_result(
        self,
        mission: Mission,
        t_start: float,
        commands_dispatched: Optional[List[Dict[str, Any]]] = None,
        command_results: Optional[List[Dict[str, Any]]] = None,
        last_verification: Optional[Any] = None,
        failure_reason: Optional[str] = None,
        safe_recovery: bool = False,
    ) -> MissionResult:
        duration = max(0.001, time.time() - t_start)
        mission.completed_at = datetime.now(timezone.utc).isoformat()

        succ_count = sum(1 for a in mission.actions if a.status == ActionStatus.COMPLETED)
        fail_count = sum(1 for a in mission.actions if a.status in [ActionStatus.FAILED, ActionStatus.TIMED_OUT])

        ver_summary = (
            last_verification.to_dict()
            if last_verification
            else {
                "status": "SKIPPED" if mission.status in [MissionState.ABORTED, MissionState.SUSPENDED] else "FAILED",
                "converged": False,
                "message": failure_reason or "No verification executed",
            }
        )

        res = MissionResult(
            mission_id=mission.mission_id,
            objective=mission.objective.name,
            status=mission.status,
            total_duration_sec=duration,
            actions_count=len(mission.actions),
            successful_actions=succ_count,
            failed_actions=fail_count,
            candidate_evaluations=[c.to_dict() for c in mission.candidates],
            selected_candidate=mission.selected_candidate.to_dict() if mission.selected_candidate else None,
            commands_dispatched=commands_dispatched or [],
            command_results=command_results or [],
            verification_summary=ver_summary,
            active_perception_insights=mission.active_perception.to_dict() if mission.active_perception else None,
            failure_reason=failure_reason,
            safe_recovery_executed=safe_recovery,
        )
        mission.result = res
        return res
