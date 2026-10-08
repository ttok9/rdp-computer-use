import importlib.util
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from rdp_cua.models import Action, ActionKind, Observation


HAS_AARDWOLF = importlib.util.find_spec("aardwolf") is not None
HAS_OPENAI = importlib.util.find_spec("openai") is not None


@unittest.skipUnless(HAS_AARDWOLF, "install the rdp extra")
class AardwolfAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        from aardwolf.commons.queuedata.constants import MOUSEBUTTON, VIDEO_FORMAT
        from rdp_cua.adapters.aardwolf_driver import AardwolfDriver

        self.driver = AardwolfDriver("192.0.2.1", "tester", "dummy", width=100, height=50)
        self.driver._video_format = VIDEO_FORMAT
        self.driver._mouse_button = MOUSEBUTTON
        self.connection = SimpleNamespace(
            desktop_buffer_has_data=True,
            send_mouse=AsyncMock(),
            send_key_char=AsyncMock(),
            send_key_scancode=AsyncMock(),
            terminate=AsyncMock(),
        )
        self.driver.connection = self.connection

    async def test_capture_and_normalized_click(self) -> None:
        class FakeImage:
            size = (100, 50)
            def save(self, output, image_format):
                self.image_format = image_format
                output.write(b"png-frame")

        self.connection.get_desktop_buffer = Mock(return_value=FakeImage())
        observation = await self.driver.capture()
        self.assertEqual(observation.image_png, b"png-frame")
        self.assertEqual((observation.width, observation.height), (100, 50))

        with patch("rdp_cua.adapters.aardwolf_driver.asyncio.sleep", new=AsyncMock()):
            await self.driver.execute(Action(ActionKind.LEFT_CLICK, coordinate=(500, 500)))
        first_call = self.connection.send_mouse.await_args_list[0]
        self.assertEqual(first_call.kwargs["xPos"], 50)
        self.assertEqual(first_call.kwargs["yPos"], 25)
        self.assertTrue(first_call.kwargs["is_pressed"])

    async def test_keyboard_and_disconnect(self) -> None:
        with patch("rdp_cua.adapters.aardwolf_driver.asyncio.sleep", new=AsyncMock()):
            await self.driver.execute(Action(ActionKind.TYPE, text="Hi"))
            await self.driver.execute(Action(ActionKind.KEY, key="ctrl+a"))
        self.assertEqual(self.connection.send_key_char.await_count, 4)
        self.assertEqual(self.connection.send_key_scancode.await_count, 4)
        await self.driver.disconnect()
        self.connection.terminate.assert_awaited_once()
        self.assertIsNone(self.driver.connection)


class FakeCompletions:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.last_request = None

    async def create(self, **kwargs):
        self.last_request = kwargs
        message = SimpleNamespace(content=self.payload)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@unittest.skipUnless(HAS_OPENAI, "install the vision extra")
class OpenAIAdapterTests(unittest.IsolatedAsyncioTestCase):
    def build_engine(self, payload: str):
        from rdp_cua.adapters.openai_vision import OpenAICompatibleVisionEngine

        engine = OpenAICompatibleVisionEngine.__new__(OpenAICompatibleVisionEngine)
        completions = FakeCompletions(payload)
        engine.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        engine.model = "mock-model"
        return engine, completions

    async def test_decision_json_maps_to_one_action(self) -> None:
        engine, completions = self.build_engine(
            '```json\n{"completed": false, "reason": "click it", '
            '"action": {"kind": "left_click", "coordinate": [250, 750]}}\n```'
        )
        decision = await engine.decide("click", Observation(b"png", 800, 600), ())
        self.assertFalse(decision.completed)
        self.assertEqual(decision.action.coordinate, (250, 750))
        request = completions.last_request
        self.assertEqual(request["model"], "mock-model")
        image_url = request["messages"][-1]["content"][1]["image_url"]["url"]
        self.assertTrue(image_url.startswith("data:image/png;base64,"))

    async def test_verification_json_maps_to_result(self) -> None:
        engine, _ = self.build_engine(
            '{"action_succeeded": true, "goal_completed": true, "summary": "visible"}'
        )
        result = await engine.verify(
            "finish",
            Action(ActionKind.KEY, key="enter"),
            Observation(b"png", 800, 600),
            (),
        )
        self.assertTrue(result.action_succeeded)
        self.assertTrue(result.goal_completed)


if __name__ == "__main__":
    unittest.main()
