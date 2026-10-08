import os
import unittest
from unittest.mock import patch

from rdp_cua.config import AppConfig


class ConfigTests(unittest.TestCase):
    def test_secrets_are_redacted(self) -> None:
        env = {
            "RDP_HOST": "192.0.2.10",
            "RDP_USERNAME": "tester",
            "RDP_PASSWORD": "example-secret",
            "CUA_VISION_MODEL": "example-model",
            "CUA_VISION_API_KEY": "example-key",
        }
        with patch.dict(os.environ, env, clear=True):
            config = AppConfig.from_env()
        config.require_real_run()
        public = config.public_dict()
        self.assertEqual(public["rdp_password"], "***")
        self.assertEqual(public["vision_api_key"], "***")
        self.assertNotIn("example-secret", repr(config))

    def test_rdp_smoke_does_not_require_vision_configuration(self) -> None:
        env = {
            "RDP_HOST": "192.0.2.10",
            "RDP_USERNAME": "tester",
            "RDP_PASSWORD": "example-secret",
        }
        with patch.dict(os.environ, env, clear=True):
            config = AppConfig.from_env()
        config.require_rdp()
        with self.assertRaisesRegex(ValueError, "CUA_VISION_MODEL"):
            config.require_real_run()


if __name__ == "__main__":
    unittest.main()
