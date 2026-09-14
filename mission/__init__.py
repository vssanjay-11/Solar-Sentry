"""Solar Sentry — Autonomous Mission Planner & Active Perception Package.

Agent 9 Ownership.
Translates Agent 8 cognitive decisions (WHAT) into autonomous action sequences (HOW),
evaluates candidates, conducts active perception to resolve epistemic uncertainty,
dispatches hardware commands through Agent 1's interface, executes closed-loop verification,
and enforces absolute safety overrides.
"""

from .types import (
    Mission,
    MissionObjective,
    MissionType,
    MissionState,
    MissionAction,
    MissionResult,
    CandidateRegion,
    Command,
    CommandResult,
    VerificationResult,
    ActionVerb,
    ActionStatus,
    VerificationStatus,
    FailureReason,
    ActivePerceptionInsight,
)
from .candidate_evaluator import CandidateEvaluator
from .active_perception import ActivePerceptionEvaluator
from .scan_planner import ScanPlanner
from .dispatcher import (
    CommandDispatcherInterface,
    SimulatedCommandDispatcher,
    HttpCommandDispatcher,
)
from .verifier import ActionVerifier
from .recovery import SafeRecoveryManager
from .planner import AutonomousMissionPlanner
from .executor import MissionExecutor
from .scheduler import MissionScheduler

__all__ = [
    "Mission",
    "MissionObjective",
    "MissionType",
    "MissionState",
    "MissionAction",
    "MissionResult",
    "CandidateRegion",
    "Command",
    "CommandResult",
    "VerificationResult",
    "ActionVerb",
    "ActionStatus",
    "VerificationStatus",
    "FailureReason",
    "ActivePerceptionInsight",
    "CandidateEvaluator",
    "ActivePerceptionEvaluator",
    "ScanPlanner",
    "CommandDispatcherInterface",
    "SimulatedCommandDispatcher",
    "HttpCommandDispatcher",
    "ActionVerifier",
    "SafeRecoveryManager",
    "AutonomousMissionPlanner",
    "MissionExecutor",
    "MissionScheduler",
]
