from __future__ import annotations

import asyncio
import math
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from .models import StepRecord, TaskResult, TaskStatus
from .protocols import DecisionEngine, DesktopDriver, Verifier


@dataclass(frozen=True, slots=True)
class RunnerConfig:
    max_steps: int = 30
    action_timeout_seconds: float = 30.0
    repeat_action_limit: int = 2
    observation_timeout_seconds: float = 15.0
    model_timeout_seconds: float = 60.0
    settle_seconds: float = 0.3

    def __post_init__(self) -> None:
        for name in ("max_steps", "repeat_action_limit"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("action_timeout_seconds", "observation_timeout_seconds", "model_timeout_seconds", "settle_seconds"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (name != "settle_seconds" and value == 0):
                raise ValueError(f"invalid {name}")


class _TaskCancelled(Exception):
    pass


class TaskControl:
    """Use from the runner's event loop; pause takes effect at stage boundaries."""

    def __init__(self) -> None:
        self._cancelled = asyncio.Event()
        self._resume_gate = asyncio.Event()
        self._resume_gate.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def cancel(self) -> None:
        self._cancelled.set()
        self._resume_gate.set()

    def pause(self) -> None:
        if not self.cancelled:
            self._resume_gate.clear()

    def resume(self) -> None:
        self._resume_gate.set()

    async def checkpoint(self) -> None:
        if self.cancelled:
            raise _TaskCancelled
        await self._resume_gate.wait()
        if self.cancelled:
            raise _TaskCancelled

    async def perform(self, operation: Callable[[], Coroutine[Any, Any, Any]], timeout: float) -> Any:
        await self.checkpoint()
        work = asyncio.create_task(operation())
        cancellation = asyncio.create_task(self._cancelled.wait())
        try:
            done, _ = await asyncio.wait({work, cancellation}, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
            if self.cancelled:
                raise _TaskCancelled
            if work not in done:
                raise TimeoutError
            return work.result()
        finally:
            for task in (work, cancellation):
                if not task.done():
                    task.cancel()
            await asyncio.gather(work, cancellation, return_exceptions=True)


class ComputerUseRunner:
    def __init__(self, driver: DesktopDriver, decision_engine: DecisionEngine, verifier: Verifier, config: RunnerConfig | None = None) -> None:
        self.driver = driver
        self.decision_engine = decision_engine
        self.verifier = verifier
        self.config = config or RunnerConfig()

    async def run(self, goal: str, control: TaskControl | None = None) -> TaskResult:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal cannot be empty")
        control = control or TaskControl()
        history: list[StepRecord] = []
        last_fingerprint = None
        consecutive_count = 0
        stage = "observation"
        try:
            for step_number in range(1, self.config.max_steps + 1):
                stage = "observation"
                before = await control.perform(self.driver.capture, self.config.observation_timeout_seconds)
                stage = "decision"
                decision = await control.perform(lambda: self.decision_engine.decide(goal, before, tuple(history)), self.config.model_timeout_seconds)
                await control.checkpoint()
                if decision.completed:
                    return TaskResult(TaskStatus.SUCCEEDED, decision.reason, tuple(history))
                action = decision.action
                assert action is not None
                fingerprint = action.fingerprint()
                consecutive_count = consecutive_count + 1 if fingerprint == last_fingerprint else 1
                last_fingerprint = fingerprint
                if consecutive_count > self.config.repeat_action_limit:
                    return TaskResult(TaskStatus.FAILED, f"identical action repeated more than {self.config.repeat_action_limit} times", tuple(history))
                stage = "action"
                await control.perform(lambda: self.driver.execute(action), self.config.action_timeout_seconds)
                if self.config.settle_seconds:
                    stage = "settle"
                    await control.perform(lambda: asyncio.sleep(self.config.settle_seconds), self.config.settle_seconds + 1)
                stage = "observation"
                after = await control.perform(self.driver.capture, self.config.observation_timeout_seconds)
                stage = "verification"
                verification = await control.perform(lambda: self.verifier.verify(goal, action, after, tuple(history)), self.config.model_timeout_seconds)
                await control.checkpoint()
                history.append(StepRecord(step_number, action, decision.reason, verification))
                if verification.goal_completed:
                    status = TaskStatus.SUCCEEDED if verification.action_succeeded else TaskStatus.FAILED
                    return TaskResult(status, verification.summary, tuple(history))
            return TaskResult(TaskStatus.MAX_STEPS, f"maximum step count ({self.config.max_steps}) reached", tuple(history))
        except _TaskCancelled:
            return TaskResult(TaskStatus.CANCELLED, "task cancelled", tuple(history))
        except TimeoutError:
            return TaskResult(TaskStatus.FAILED, f"{stage} timed out", tuple(history))
        except Exception as exc:
            # Third-party exceptions may include URLs, credentials, or typed content.
            return TaskResult(TaskStatus.FAILED, f"{stage} failed ({type(exc).__name__})", tuple(history))
