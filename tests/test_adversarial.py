"""Adversarial contracts and real SDK serialization, without network access."""
import asyncio
import base64
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from rdp_cua.adapters.openai_vision import OpenAICompatibleVisionEngine
from rdp_cua.models import Action, ActionKind, Decision, Observation, TaskStatus, Verification
from rdp_cua.runner import ComputerUseRunner, RunnerConfig, TaskControl

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")


class CancellationOrderTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_then_pause_cannot_deadlock(self):
        control = TaskControl()
        control.cancel()
        control.pause()
        driver = SimpleNamespace(capture=AsyncMock(), execute=AsyncMock())
        engine = SimpleNamespace(decide=AsyncMock(), verify=AsyncMock())
        result = await asyncio.wait_for(ComputerUseRunner(driver, engine, engine).run("goal", control), .2)
        self.assertEqual(result.status, TaskStatus.CANCELLED)
        driver.capture.assert_not_awaited()

    async def test_cancel_while_paused_unblocks(self):
        control = TaskControl()
        control.pause()
        driver = SimpleNamespace(capture=AsyncMock(), execute=AsyncMock())
        engine = SimpleNamespace(decide=AsyncMock(), verify=AsyncMock())
        task = asyncio.create_task(ComputerUseRunner(driver, engine, engine).run("goal", control))
        await asyncio.sleep(0)
        control.cancel()
        self.assertEqual((await asyncio.wait_for(task, .2)).status, TaskStatus.CANCELLED)

    async def test_verifier_timeout_is_bounded(self):
        async def never(*args):
            await asyncio.Event().wait()
        driver = SimpleNamespace(capture=AsyncMock(return_value=Observation(PNG, 1, 1)), execute=AsyncMock())
        engine = SimpleNamespace(decide=AsyncMock(return_value=Decision(False, "act", Action(ActionKind.KEY, key="enter"))), verify=AsyncMock(side_effect=never))
        result = await ComputerUseRunner(driver, engine, engine, RunnerConfig(model_timeout_seconds=.01, settle_seconds=0)).run("goal")
        self.assertEqual(result.reason, "verification timed out")


class JSONBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def engine_with_text(self, content):
        engine = OpenAICompatibleVisionEngine.__new__(OpenAICompatibleVisionEngine)
        engine.model = "synthetic-model"
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
        engine.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=response))))
        return engine

    async def test_duplicate_json_keys_are_rejected(self):
        engine = self.engine_with_text('{"completed":false,"completed":true,"reason":"contradiction","action":null}')
        with self.assertRaises(ValueError):
            await engine.decide("goal", Observation(PNG, 1, 1), ())

    async def test_nonstandard_json_constants_are_rejected(self):
        engine = self.engine_with_text('{"completed":true,"reason":"done","action":null,"extra":NaN}')
        with self.assertRaises(ValueError):
            await engine.decide("goal", Observation(PNG, 1, 1), ())

    async def test_invalid_response_shapes_are_rejected(self):
        for content in (None, "[]", "null", "not json", '{"completed":1}', '{"completed":false,"action":[]}'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                await self.engine_with_text(content).decide("goal", Observation(PNG, 1, 1), ())

    async def test_valid_fenced_json_is_accepted(self):
        engine = self.engine_with_text('```json\n{"completed":true,"reason":"visible","action":null}\n```')
        self.assertTrue((await engine.decide("goal", Observation(PNG, 1, 1), ())).completed)

    async def test_prompt_does_not_require_click_fields_for_typing(self):
        engine = self.engine_with_text('{"completed":false,"reason":"type","action":{"kind":"type","text":"hello"}}')
        decision = await engine.decide("goal", Observation(PNG, 1, 1), ())
        prompt = engine.client.chat.completions.create.await_args.kwargs['messages'][-1]['content'][0]['text']
        self.assertIn('omit fields that do not belong', prompt)
        self.assertEqual(decision.action.text, "hello")


@unittest.skipUnless(importlib.util.find_spec("openai"), "vision extra not installed")
class RealSDKTransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import httpx
        from openai import AsyncOpenAI
        self.httpx = httpx
        self.requests = []
        self.status = 200
        self.content = json.dumps({"completed": False, "reason": "focus", "action": {"kind": "left_click", "coordinate": [500, 500]}})
        def handle(request):
            self.requests.append(request)
            if self.status != 200:
                return httpx.Response(self.status, json={"error": {"message": "synthetic failure", "type": "test_error"}})
            return httpx.Response(200, json={"id": "synthetic", "object": "chat.completion", "created": 0, "model": "synthetic-model", "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": self.content}}]})
        self.http = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        self.engine = OpenAICompatibleVisionEngine.__new__(OpenAICompatibleVisionEngine)
        self.engine.model = "synthetic-model"
        self.engine.client = AsyncOpenAI(base_url="https://example.invalid/v1", api_key="synthetic-test-key", max_retries=0, http_client=self.http)

    async def asyncTearDown(self):
        await self.engine.close()

    async def test_real_sdk_serializes_image_and_one_action(self):
        decision = await self.engine.decide("test goal", Observation(PNG, 1, 1), ())
        self.assertEqual(decision.action.coordinate, (500, 500))
        self.assertEqual(self.requests[0].url.path, "/v1/chat/completions")
        body = json.loads(self.requests[0].content)
        self.assertEqual(body["model"], "synthetic-model")
        self.assertEqual(body["messages"][0]["role"], "system")
        url = body["messages"][-1]["content"][1]["image_url"]["url"]
        self.assertEqual(base64.b64decode(url.split(",", 1)[1]), PNG)

    async def test_real_sdk_verification_contract(self):
        self.content = json.dumps({"action_succeeded": True, "goal_completed": True, "summary": "visible synthetic result"})
        result = await self.engine.verify("goal", Action(ActionKind.TYPE, text="public sample"), Observation(PNG, 1, 1), ())
        self.assertTrue(result.goal_completed)
        self.assertIn("public sample", self.requests[0].content.decode())

    async def test_http_error_does_not_lead_to_input(self):
        self.status = 401
        driver = SimpleNamespace(capture=AsyncMock(return_value=Observation(PNG, 1, 1)), execute=AsyncMock())
        result = await ComputerUseRunner(driver, self.engine, self.engine, RunnerConfig(settle_seconds=0)).run("goal")
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertIn("AuthenticationError", result.reason)
        self.assertNotIn("synthetic failure", result.reason)
        self.assertEqual(len(self.requests), 1)
        driver.execute.assert_not_awaited()

    async def test_close_releases_http_client(self):
        await self.engine.close()
        self.assertTrue(self.http.is_closed)
