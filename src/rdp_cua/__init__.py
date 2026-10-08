"""Agentless Windows GUI automation over RDP."""

from .models import Action, ActionKind, Decision, Observation, TaskResult, TaskStatus
from .runner import ComputerUseRunner, RunnerConfig, TaskControl

__all__ = [
    "Action",
    "ActionKind",
    "ComputerUseRunner",
    "Decision",
    "Observation",
    "RunnerConfig",
    "TaskControl",
    "TaskResult",
    "TaskStatus",
]

__version__ = "0.2.0a2"
