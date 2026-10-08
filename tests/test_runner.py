import asyncio
import unittest
from collections import deque
from typing import Sequence

from rdp_cua.models import Action, ActionKind, Decision, Observation, StepRecord, TaskStatus, Verification
from rdp_cua.runner import ComputerUseRunner, RunnerConfig, TaskControl


class MockDriver:
    def __init__(self, delay: float = 0) -> None:
        self.actions: list[Action] = []
        self.delay = delay

    async def capture(self) -> Observation:
        return Observation(b"frame", 1280, 720)

    async def execute(self, action: Action) -> None:
        if self.delay:
            await asyncio.sleep(self.delay)
        self.actions.append(action)


class ScriptedEngine:
    def __init__(self, decisions: list[Decision], complete_after: int | None = None) -> None:
        self.decisions = deque(decisions)
        self.verification_count = 0
        self.complete_after = complete_after

    async def decide(self, goal: str, observation: Observation, history: Sequence[StepRecord]) -> Decision:
        return self.decisions.popleft()

    async def verify(
        self,
        goal: str,
        action: Action,
        observation: Observation,
        history: Sequence[StepRecord],
    ) -> Verification:
        self.verification_count += 1
        completed = self.complete_after == self.verification_count
        return Verification(True, completed, "visible mock result")


class RunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_completes_after_verified_action(self) -> None:
        driver = MockDriver()
        engine = ScriptedEngine(
            [Decision(False, "click target", Action(ActionKind.LEFT_CLICK, coordinate=(500, 500)))],
            complete_after=1,
        )
        result = await ComputerUseRunner(driver, engine, engine).run("click target")
        self.assertEqual(result.status, TaskStatus.SUCCEEDED)
        self.assertEqual(len(result.steps), 1)

    async def test_repeat_guard_stops_third_identical_action(self) -> None:
        action = Action(ActionKind.KEY, key="enter")
        driver = MockDriver()
        engine = ScriptedEngine([Decision(False, "retry", action) for _ in range(3)])
        runner = ComputerUseRunner(driver, engine, engine, RunnerConfig(repeat_action_limit=2))
        result = await runner.run("press enter")
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertEqual(len(driver.actions), 2)

    async def test_cancelled_before_first_action(self) -> None:
        driver = MockDriver()
        engine = ScriptedEngine([Decision(True, "done")])
        control = TaskControl()
        control.cancel()
        result = await ComputerUseRunner(driver, engine, engine).run("anything", control)
        self.assertEqual(result.status, TaskStatus.CANCELLED)

    async def test_pause_blocks_until_resume(self) -> None:
        driver = MockDriver()
        engine = ScriptedEngine([Decision(True, "done")])
        control = TaskControl()
        control.pause()
        task = asyncio.create_task(ComputerUseRunner(driver, engine, engine).run("anything", control))
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        control.resume()
        result = await task
        self.assertEqual(result.status, TaskStatus.SUCCEEDED)

    async def test_action_timeout_returns_failed_result(self) -> None:
        driver = MockDriver(delay=0.05)
        engine = ScriptedEngine(
            [Decision(False, "slow action", Action(ActionKind.KEY, key="enter"))]
        )
        runner = ComputerUseRunner(
            driver,
            engine,
            engine,
            RunnerConfig(action_timeout_seconds=0.001),
        )
        result = await runner.run("time out safely")
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertEqual(result.reason, "action timed out")

    async def test_max_steps_returns_structured_result(self) -> None:
        driver = MockDriver()
        engine = ScriptedEngine(
            [Decision(False, "first", Action(ActionKind.KEY, key="enter"))]
        )
        runner = ComputerUseRunner(driver, engine, engine, RunnerConfig(max_steps=1))
        result = await runner.run("one step only")
        self.assertEqual(result.status, TaskStatus.MAX_STEPS)
        self.assertEqual(len(result.steps), 1)


if __name__ == "__main__":
    unittest.main()
