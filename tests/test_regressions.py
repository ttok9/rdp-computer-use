import asyncio
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from rdp_cua.cli import main
from rdp_cua.config import load_env_file
from rdp_cua.models import Action, ActionKind, Decision, Observation, Verification, TaskStatus
from rdp_cua.runner import ComputerUseRunner, RunnerConfig, TaskControl
from rdp_cua.scenario import Scenario
from rdp_cua.adapters.aardwolf_driver import AardwolfDriver
from rdp_cua.adapters.openai_vision import OpenAICompatibleVisionEngine


class ModelValidationTests(unittest.TestCase):
    def test_rejects_ambiguous_or_unbounded_actions(self):
        cases = [
            {"kind": "left_click", "coordinate": [True, 5]},
            {"kind": "left_click", "coordinate": [1.5, 5]},
            {"kind": "type", "text": 123},
            {"kind": "key", "key": "enter", "text": "also type"},
            {"kind": "wait", "seconds": float("nan")},
            {"kind": "wait", "seconds": float("inf")},
            {"kind": "wait", "seconds": 301},
            {"kind": "scroll", "scroll_delta": 100000},
            {"kind": "wait", "seconds": 0, "extra": "unexpected"},
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                Action.from_mapping(payload)

    def test_string_booleans_are_not_success(self):
        with self.assertRaises(ValueError):
            Decision("false", "not complete")
        with self.assertRaises(ValueError):
            Verification("false", True, "not complete")

    def test_nonfinite_runtime_limits_rejected(self):
        for value in (float('nan'), float('inf'), -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                RunnerConfig(model_timeout_seconds=value)

    def test_duplicate_scenario_steps_rejected(self):
        with self.assertRaises(ValueError):
            Scenario.from_mapping({"title": "t", "goal": "g", "steps": [
                {"number": 1, "title": "one"}, {"number": 1, "title": "two"}]})

    def test_env_file_is_literal_and_environment_wins(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"RDP_HOST": "existing"}, clear=True):
            path = Path(directory) / "settings"
            path.write_text('RDP_HOST=ignored\nRDP_PASSWORD="$(not-a-command)#literal"\n', encoding="utf-8")
            load_env_file(path)
            self.assertEqual(os.environ['RDP_HOST'], 'existing')
            self.assertEqual(os.environ['RDP_PASSWORD'], '$(not-a-command)#literal')

    def test_invalid_env_does_not_partially_modify_environment(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / "settings"
            path.write_text('RDP_HOST=new\ninvalid line\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_env_file(path)
            self.assertNotIn('RDP_HOST', os.environ)

    def test_cli_scenario_and_error_output(self):
        path = Path(__file__).parents[1] / 'examples/scenarios/notepad.json'
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(['scenario-check', str(path)]), 0)
        self.assertTrue(json.loads(out.getvalue())['valid'])
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(main(['run', '--goal', 'x', '--env-file', 'missing-env']), 2)
        self.assertNotIn('Traceback', err.getvalue())


class RuntimeRegressionTests(unittest.IsolatedAsyncioTestCase):
    def make_runner(self, config=None):
        self.driver = SimpleNamespace(capture=AsyncMock(return_value=Observation(b'frame', 100, 100)), execute=AsyncMock())
        action = Action(ActionKind.KEY, key='enter')
        self.engine = SimpleNamespace(decide=AsyncMock(return_value=Decision(False, 'next', action)), verify=AsyncMock(return_value=Verification(True, False, 'continue')))
        return ComputerUseRunner(self.driver, self.engine, self.engine, config or RunnerConfig(settle_seconds=0))

    async def test_cancel_during_inference_prevents_input(self):
        runner = self.make_runner()
        entered = asyncio.Event()
        async def pending(*args):
            entered.set()
            await asyncio.Event().wait()
        self.engine.decide.side_effect = pending
        control = TaskControl()
        task = asyncio.create_task(runner.run('goal', control))
        await asyncio.wait_for(entered.wait(), 1)
        control.cancel()
        result = await asyncio.wait_for(task, 1)
        self.assertEqual(result.status, TaskStatus.CANCELLED)
        self.driver.execute.assert_not_awaited()

    async def test_cancel_during_action_cancels_child_coroutine(self):
        runner = self.make_runner()
        entered, cleaned = asyncio.Event(), asyncio.Event()
        async def action(*args):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
        self.driver.execute.side_effect = action
        control = TaskControl()
        task = asyncio.create_task(runner.run('goal', control))
        await asyncio.wait_for(entered.wait(), 1)
        control.cancel()
        self.assertEqual((await asyncio.wait_for(task, 1)).status, TaskStatus.CANCELLED)
        self.assertTrue(cleaned.is_set())

    async def test_failed_checks_do_not_reset_repeat_guard(self):
        runner = self.make_runner()
        self.engine.verify.return_value = Verification(False, False, 'still wrong')
        result = await runner.run('goal')
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertEqual(self.driver.execute.await_count, 2)

    async def test_inference_timeout_does_not_execute_input(self):
        runner = self.make_runner(RunnerConfig(model_timeout_seconds=0.01, settle_seconds=0))
        async def pending(*args):
            await asyncio.Event().wait()
        self.engine.decide.side_effect = pending
        result = await runner.run('goal')
        self.assertEqual(result.reason, 'decision timed out')
        self.driver.execute.assert_not_awaited()

    async def test_capture_timeout_is_bounded(self):
        runner = self.make_runner(RunnerConfig(observation_timeout_seconds=0.01, settle_seconds=0))
        async def pending():
            await asyncio.Event().wait()
        self.driver.capture.side_effect = pending
        self.assertEqual((await runner.run('goal')).reason, 'observation timed out')

    async def test_exception_text_is_not_leaked(self):
        runner = self.make_runner()
        self.driver.capture.side_effect = RuntimeError('credential-example-do-not-log')
        result = await runner.run('goal')
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertNotIn('credential-example', result.reason)

    async def test_external_task_cancellation_propagates(self):
        runner = self.make_runner()
        entered = asyncio.Event()
        async def pending(*args):
            entered.set()
            await asyncio.Event().wait()
        self.engine.decide.side_effect = pending
        task = asyncio.create_task(runner.run('goal'))
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task


class AdapterRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_bad_key_is_validated_before_pressing_modifiers(self):
        driver = AardwolfDriver('example.invalid', 'demo', 'dummy')
        driver.connection = SimpleNamespace(send_key_scancode=AsyncMock())
        with self.assertRaises(ValueError):
            await driver.execute(Action(ActionKind.KEY, key='ctrl+unsupported'))
        driver.connection.send_key_scancode.assert_not_awaited()

    async def test_key_release_after_transmission_failure(self):
        driver = AardwolfDriver('example.invalid', 'demo', 'dummy')
        send = AsyncMock(side_effect=[None, (None, RuntimeError('failed')), None, None])
        driver.connection = SimpleNamespace(send_key_scancode=send)
        with self.assertRaises(RuntimeError):
            await driver.execute(Action(ActionKind.KEY, key='ctrl+a'))
        self.assertEqual(send.await_args_list[-1].args, (0x1D, False, False))

    async def test_scroll_uses_signed_wheel_not_arrow_keys(self):
        driver = AardwolfDriver('example.invalid', 'demo', 'dummy')
        driver._mouse_button = SimpleNamespace(MOUSEBUTTON_WHEEL_UP='wheel')
        driver.connection = SimpleNamespace(send_mouse=AsyncMock(), send_key_scancode=AsyncMock())
        await driver.execute(Action(ActionKind.SCROLL, scroll_delta=-2))
        self.assertEqual(driver.connection.send_mouse.await_count, 2)
        self.assertEqual(driver.connection.send_mouse.await_args.kwargs['steps'], -120)
        driver.connection.send_key_scancode.assert_not_awaited()

    async def test_verifier_receives_action_parameters(self):
        engine = OpenAICompatibleVisionEngine.__new__(OpenAICompatibleVisionEngine)
        engine._ask = AsyncMock(return_value={'action_succeeded': True, 'goal_completed': False, 'summary': 'visible'})
        await engine.verify('goal', Action(ActionKind.TYPE, text='sample text'), Observation(b'frame', 100, 100), ())
        self.assertIn('sample text', engine._ask.await_args.args[1])

    async def test_string_false_from_model_is_rejected(self):
        engine = OpenAICompatibleVisionEngine.__new__(OpenAICompatibleVisionEngine)
        engine._ask = AsyncMock(return_value={'completed': 'false', 'action': None})
        with self.assertRaises(ValueError):
            await engine.decide('goal', Observation(b'frame', 100, 100), ())

    async def test_frame_dimensions_follow_actual_image(self):
        driver = AardwolfDriver('example.invalid', 'demo', 'dummy')
        class Frame:
            size = (800, 600)
            def save(self, output, kind):
                output.write(b'frame')
        driver._video_format = SimpleNamespace(PIL='pil')
        driver.connection = SimpleNamespace(desktop_buffer_has_data=True, get_desktop_buffer=lambda _: Frame())
        observation = await driver.capture()
        self.assertEqual((observation.width, observation.height), (800, 600))


if __name__ == '__main__':
    unittest.main()
