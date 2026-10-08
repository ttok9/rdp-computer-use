from __future__ import annotations

from typing import Protocol, Sequence

from .models import Action, Decision, Observation, StepRecord, Verification


class DesktopDriver(Protocol):
    async def capture(self) -> Observation:
        """Return the latest desktop frame."""

    async def execute(self, action: Action) -> None:
        """Execute one validated action."""


class DecisionEngine(Protocol):
    async def decide(
        self,
        goal: str,
        observation: Observation,
        history: Sequence[StepRecord],
    ) -> Decision:
        """Return completion or exactly one next action."""


class Verifier(Protocol):
    async def verify(
        self,
        goal: str,
        action: Action,
        observation: Observation,
        history: Sequence[StepRecord],
    ) -> Verification:
        """Verify the action result and goal state from the new frame."""

