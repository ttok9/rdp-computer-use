import asyncio
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from rdp_cua.adapters.aardwolf_driver import AardwolfDriver
from rdp_cua.cli import _real_run, main
from rdp_cua.config import AppConfig
from rdp_cua.models import Action, ActionKind

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from check_release import check, selected_files


class ReleaseSafetyTests(unittest.TestCase):
    def test_public_tree_passes_content_and_link_checks(self):
        self.assertGreater(len(check()), 30)

    def test_source_selection_excludes_secrets_and_build_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "public.py").write_text("pass\n")
            (root / "src" / "__pycache__").mkdir()
            (root / "src" / "__pycache__" / "ignored.py").write_text("pass\n")
            (root / ".env").write_text("dummy=value\n")
            (root / "result.json").write_text("{}")
            self.assertEqual([p.name for p in selected_files(root)], ["public.py"])

    def test_source_selection_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            try:
                (root / "docs" / "outside.md").symlink_to(root / "missing.md")
            except OSError:
                self.skipTest("symlinks not available on this platform")
            with self.assertRaises(ValueError):
                selected_files(root)

    def test_cli_refuses_existing_output_before_connecting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_text("keep")
            with patch("rdp_cua.cli._real_run") as run, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["run", "--goal", "demo", "--output", str(path)]), 2)
            run.assert_not_called()
            self.assertEqual(path.read_text(), "keep")

    @unittest.skipUnless(importlib.util.find_spec("aardwolf"), "rdp extra not installed")
    def test_real_factory_parses_nla_credentials_and_port(self):
        from aardwolf.commons.factory import RDPConnectionFactory
        from aardwolf.commons.iosettings import RDPIOSettings
        driver = AardwolfDriver("192.0.2.10", "test user", "dummy@pass:word", domain="LAB", port=3390)
        factory = RDPConnectionFactory.from_url(driver._rdp_url(), RDPIOSettings())
        credential = factory.get_credential()
        self.assertEqual(credential.username, "test user")
        self.assertEqual(credential.domain, "LAB")
        self.assertEqual(factory.get_target().port, 3390)


class CleanupSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_modifiers_release_even_if_main_release_fails(self):
        driver = AardwolfDriver("example.invalid", "demo", "dummy")
        send = AsyncMock(side_effect=[None, None, (None, RuntimeError("release failed")), None])
        driver.connection = SimpleNamespace(send_key_scancode=send)
        with self.assertRaises(RuntimeError):
            await driver.execute(Action(ActionKind.KEY, key="ctrl+a"))
        self.assertEqual(send.await_args_list[-1].args, (0x1D, False, False))

    async def test_type_release_attempted_after_press_failure(self):
        driver = AardwolfDriver("example.invalid", "demo", "dummy")
        send = AsyncMock(side_effect=[(None, RuntimeError("failed")), None])
        driver.connection = SimpleNamespace(send_key_char=send)
        with self.assertRaises(RuntimeError):
            await driver.execute(Action(ActionKind.TYPE, text="A"))
        self.assertEqual(send.await_args_list[-1].args, ("A", False))

    async def test_cli_closes_both_clients_after_connect_failure(self):
        driver = SimpleNamespace(connect=AsyncMock(side_effect=TimeoutError), disconnect=AsyncMock())
        engine = SimpleNamespace(close=AsyncMock())
        config = AppConfig("192.0.2.10", 3389, "demo", "dummy", vision_model="test-model")
        with patch("rdp_cua.cli.AppConfig.from_env", return_value=config), \
             patch("rdp_cua.adapters.aardwolf_driver.AardwolfDriver", return_value=driver), \
             patch("rdp_cua.adapters.openai_vision.OpenAICompatibleVisionEngine", return_value=engine):
            with self.assertRaises(TimeoutError):
                await _real_run("goal")
        driver.disconnect.assert_awaited_once()
        engine.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
