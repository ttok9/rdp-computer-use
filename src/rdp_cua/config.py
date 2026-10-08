from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AppConfig:
    rdp_host: str
    rdp_port: int
    rdp_username: str
    rdp_password: str = field(repr=False)
    rdp_domain: str = ""
    width: int = 1920
    height: int = 1080
    vision_base_url: str = "http://127.0.0.1:8000/v1"
    vision_model: str = ""
    vision_api_key: str = field(default="not-required", repr=False)
    max_steps: int = 30
    action_timeout_seconds: float = 30.0
    repeat_action_limit: int = 2
    observation_timeout_seconds: float = 15.0
    model_timeout_seconds: float = 60.0
    settle_seconds: float = 0.3
    rdp_auth: str = "ntlm"

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            rdp_host=os.getenv("RDP_HOST", ""),
            rdp_port=int(os.getenv("RDP_PORT", "3389")),
            rdp_username=os.getenv("RDP_USERNAME", ""),
            rdp_password=os.getenv("RDP_PASSWORD", ""),
            rdp_domain=os.getenv("RDP_DOMAIN", ""),
            width=int(os.getenv("RDP_WIDTH", "1920")),
            height=int(os.getenv("RDP_HEIGHT", "1080")),
            vision_base_url=os.getenv("CUA_VISION_BASE_URL", "http://127.0.0.1:8000/v1"),
            vision_model=os.getenv("CUA_VISION_MODEL", ""),
            vision_api_key=os.getenv("CUA_VISION_API_KEY", "not-required"),
            max_steps=int(os.getenv("CUA_MAX_STEPS", "30")),
            action_timeout_seconds=float(os.getenv("CUA_ACTION_TIMEOUT_SECONDS", "30")),
            repeat_action_limit=int(os.getenv("CUA_REPEAT_ACTION_LIMIT", "2")),
            observation_timeout_seconds=float(os.getenv("CUA_OBSERVATION_TIMEOUT_SECONDS", "15")),
            model_timeout_seconds=float(os.getenv("CUA_MODEL_TIMEOUT_SECONDS", "60")),
            settle_seconds=float(os.getenv("CUA_SETTLE_SECONDS", "0.3")),
            rdp_auth=os.getenv("RDP_AUTH", "ntlm"),
        )

    def require_real_run(self) -> None:
        self.require_rdp()
        missing = [
            name
            for name, value in {
                "CUA_VISION_MODEL": self.vision_model,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError("missing required environment variables: " + ", ".join(missing))
        url = urlsplit(self.vision_base_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            raise ValueError("vision endpoint must be an HTTP(S) URL without embedded credentials")
        from .runner import RunnerConfig
        RunnerConfig(self.max_steps, self.action_timeout_seconds, self.repeat_action_limit,
                     self.observation_timeout_seconds, self.model_timeout_seconds, self.settle_seconds)
        if self.width <= 0 or self.height <= 0:
            raise ValueError("RDP dimensions must be positive")

    def require_rdp(self) -> None:
        if self.rdp_auth not in {"ntlm", "tls"}:
            raise ValueError("RDP_AUTH must be ntlm or tls")
        missing = [
            name
            for name, value in {
                "RDP_HOST": self.rdp_host,
                "RDP_USERNAME": self.rdp_username,
                "RDP_PASSWORD": self.rdp_password,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError("missing required environment variables: " + ", ".join(missing))
        if self.width <= 0 or self.height <= 0:
            raise ValueError("RDP dimensions must be positive")
        if not 1 <= self.rdp_port <= 65535:
            raise ValueError("RDP_PORT must be within 1..65535")
        if any(char in self.rdp_host for char in '/@?#'):
            raise ValueError("RDP_HOST must be a hostname or IP address")

    def public_dict(self) -> dict[str, object]:
        return {
            "rdp_host": self.rdp_host,
            "rdp_port": self.rdp_port,
            "rdp_username": self.rdp_username,
            "rdp_password": "***" if self.rdp_password else "",
            "rdp_domain": self.rdp_domain,
            "rdp_auth": self.rdp_auth,
            "width": self.width,
            "height": self.height,
            "vision_base_url": self.vision_base_url,
            "vision_model": self.vision_model,
            "vision_api_key": "***" if self.vision_api_key else "",
            "max_steps": self.max_steps,
            "action_timeout_seconds": self.action_timeout_seconds,
            "repeat_action_limit": self.repeat_action_limit,
            "observation_timeout_seconds": self.observation_timeout_seconds,
            "model_timeout_seconds": self.model_timeout_seconds,
            "settle_seconds": self.settle_seconds,
        }


def load_env_file(path: str | Path) -> None:
    """Read literal KEY=value pairs; never execute shell code or expand variables.

    Existing process environment wins. Quotes surrounding the whole value are
    removed. Inline comments and multiline values are deliberately unsupported.
    """
    import re
    values = {}
    for number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"invalid env assignment at line {number}")
        if value[:1] in {'\"', "'"}:
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError(f"unclosed env quote at line {number}")
            value = value[1:-1]
        values[key] = value
    for key, value in values.items():
        os.environ.setdefault(key, value)
