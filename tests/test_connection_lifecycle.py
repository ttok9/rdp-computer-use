"""Connection/CLI lifecycle with fake sessions. Never connects to a real host."""
import asyncio
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from rdp_cua.adapters.aardwolf_driver import AardwolfDriver
from rdp_cua.cli import _real_run, _smoke_rdp, main
from rdp_cua.config import AppConfig
from rdp_cua.models import Observation, TaskResult, TaskStatus


@unittest.skipUnless(importlib.util.find_spec('aardwolf'), 'rdp extra not installed')
class RDPConnectionLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def prepare(self, auth='ntlm'):
        self.driver = AardwolfDriver('192.0.2.1', 'tester', 'dummy', auth=auth)
        self.connection = SimpleNamespace(connect=AsyncMock(return_value=(True, None)), terminate=AsyncMock())
        self.factory = SimpleNamespace(create_connection_newtarget=Mock(return_value=self.connection))

    async def test_nla_settings_and_connect(self):
        from aardwolf.protocol.x224.constants import SUPP_PROTOCOLS
        self.prepare()
        with patch('aardwolf.commons.factory.RDPConnectionFactory.from_url', return_value=self.factory) as factory, patch('rdp_cua.adapters.aardwolf_driver.asyncio.sleep', new=AsyncMock()):
            await self.driver.connect()
        settings = factory.call_args.args[1]
        self.assertEqual(settings.supported_protocols, SUPP_PROTOCOLS.HYBRID)
        self.assertEqual(settings.channels, [])
        self.assertFalse(settings.clipboard_use_pyperclip)
        await self.driver.disconnect()
        self.connection.terminate.assert_awaited_once()

    async def test_explicit_legacy_tls_settings(self):
        from aardwolf.protocol.x224.constants import SUPP_PROTOCOLS
        self.prepare('tls')
        with patch('aardwolf.commons.factory.RDPConnectionFactory.from_url', return_value=self.factory) as factory, patch('rdp_cua.adapters.aardwolf_driver.asyncio.sleep', new=AsyncMock()):
            await self.driver.connect()
        self.assertEqual(factory.call_args.args[1].supported_protocols, SUPP_PROTOCOLS.SSL)
        await self.driver.disconnect()

    async def test_connect_error_terminates_session(self):
        self.prepare()
        self.connection.connect.return_value = (None, RuntimeError('synthetic failure'))
        with patch('aardwolf.commons.factory.RDPConnectionFactory.from_url', return_value=self.factory), self.assertRaises(RuntimeError):
            await self.driver.connect()
        self.connection.terminate.assert_awaited_once()
        self.assertIsNone(self.driver.connection)

    async def test_connect_cancellation_terminates_session(self):
        self.prepare()
        self.connection.connect.side_effect = asyncio.CancelledError
        with patch('aardwolf.commons.factory.RDPConnectionFactory.from_url', return_value=self.factory), self.assertRaises(asyncio.CancelledError):
            await self.driver.connect()
        self.connection.terminate.assert_awaited_once()

    async def test_disconnect_is_idempotent(self):
        self.prepare()
        self.driver.connection = self.connection
        await self.driver.disconnect()
        await self.driver.disconnect()
        self.connection.terminate.assert_awaited_once()


class CLILifecycleTests(unittest.IsolatedAsyncioTestCase):
    def prepare(self):
        self.config = AppConfig('192.0.2.1', 3389, 'tester', 'dummy', vision_model='synthetic')
        self.driver = SimpleNamespace(connect=AsyncMock(), disconnect=AsyncMock(), capture=AsyncMock(return_value=Observation(b'synthetic', 800, 600)), execute=AsyncMock())

    async def test_smoke_receives_frame_without_input(self):
        self.prepare()
        with patch('rdp_cua.cli.AppConfig.from_env', return_value=self.config), patch('rdp_cua.adapters.aardwolf_driver.AardwolfDriver', return_value=self.driver), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(await _smoke_rdp(.1), 0)
        self.assertTrue(json.loads(output.getvalue())['frame_received'])
        self.driver.execute.assert_not_awaited()
        self.driver.disconnect.assert_awaited_once()

    async def test_smoke_connect_failure_is_sanitized(self):
        self.prepare()
        self.driver.connect.side_effect = RuntimeError('do-not-echo-this-secret')
        with patch('rdp_cua.cli.AppConfig.from_env', return_value=self.config), patch('rdp_cua.adapters.aardwolf_driver.AardwolfDriver', return_value=self.driver), contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(await _smoke_rdp(.1), 2)
        self.assertNotIn('do-not-echo', output.getvalue())
        self.driver.disconnect.assert_awaited_once()

    async def test_smoke_hung_capture_times_out(self):
        self.prepare()
        async def never():
            await asyncio.Event().wait()
        self.driver.capture.side_effect = never
        with patch('rdp_cua.cli.AppConfig.from_env', return_value=self.config), patch('rdp_cua.adapters.aardwolf_driver.AardwolfDriver', return_value=self.driver), contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(await _smoke_rdp(.01), 2)
        self.assertEqual(json.loads(output.getvalue())['error_type'], 'TimeoutError')
        self.driver.disconnect.assert_awaited_once()

    async def test_run_writes_result_and_closes_clients(self):
        self.prepare()
        engine = SimpleNamespace(close=AsyncMock())
        runner = SimpleNamespace(run=AsyncMock(return_value=TaskResult(TaskStatus.SUCCEEDED, 'synthetic', ())))
        with tempfile.TemporaryDirectory() as directory, patch('rdp_cua.cli.AppConfig.from_env', return_value=self.config), patch('rdp_cua.adapters.aardwolf_driver.AardwolfDriver', return_value=self.driver), patch('rdp_cua.adapters.openai_vision.OpenAICompatibleVisionEngine', return_value=engine), patch('rdp_cua.cli.ComputerUseRunner', return_value=runner), contextlib.redirect_stdout(io.StringIO()) as output:
            target = Path(directory) / 'result.json'
            self.assertEqual(await _real_run('goal', str(target)), 0)
            self.assertEqual(json.loads(target.read_text()), json.loads(output.getvalue()))
        self.driver.disconnect.assert_awaited_once()
        engine.close.assert_awaited_once()


class CLIValidationTests(unittest.TestCase):
    def test_invalid_timeouts_never_connect(self):
        for value in ('nan', 'inf', '-1', '0'):
            with self.subTest(value=value), patch('rdp_cua.cli._smoke_rdp') as smoke, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['smoke-rdp', '--frame-timeout', value]), 2)
                smoke.assert_not_called()

    def test_missing_output_directory_never_connects(self):
        with tempfile.TemporaryDirectory() as directory, patch('rdp_cua.cli._real_run') as run, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['run', '--goal', 'test', '--output', str(Path(directory) / 'missing/result.json')]), 2)
            run.assert_not_called()

    def test_goal_and_scenario_are_mutually_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(['run', '--goal', 'test', '--scenario', 'unused.json'])
        self.assertEqual(error.exception.code, 2)
