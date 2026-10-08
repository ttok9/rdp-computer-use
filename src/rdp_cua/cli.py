from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import platform
import math
import sys
from pathlib import Path
from collections import deque
from typing import Sequence

from .config import AppConfig, load_env_file
from .models import Action, ActionKind, Decision, Observation, StepRecord, Verification
from .runner import ComputerUseRunner, RunnerConfig


class _DemoDriver:
    def __init__(self) -> None:
        self.actions: list[Action] = []

    async def capture(self) -> Observation:
        return Observation(b"mock-png-frame", 1920, 1080)

    async def execute(self, action: Action) -> None:
        self.actions.append(action)


class _DemoEngine:
    def __init__(self) -> None:
        self.decisions = deque(
            [
                Decision(False, "focus the editor", Action(ActionKind.LEFT_CLICK, coordinate=(500, 500))),
                Decision(False, "enter the requested text", Action(ActionKind.TYPE, text="Hello")),
                Decision(True, "the mock goal is complete"),
            ]
        )

    async def decide(
        self,
        goal: str,
        observation: Observation,
        history: Sequence[StepRecord],
    ) -> Decision:
        return self.decisions.popleft()

    async def verify(
        self,
        goal: str,
        action: Action,
        observation: Observation,
        history: Sequence[StepRecord],
    ) -> Verification:
        return Verification(True, False, f"mock accepted {action.kind.value}")


def _doctor(require_adapters: bool = False) -> int:
    checks = {
        "python": platform.python_version(),
        "python_supported": sys.version_info >= (3, 11),
        "aardwolf_extra": importlib.util.find_spec("aardwolf") is not None,
        "openai_extra": importlib.util.find_spec("openai") is not None,
    }
    checks["adapter_import_errors"] = []
    if require_adapters:
        for module in ("aardwolf.commons.factory", "openai"):
            try:
                __import__(module)
            except Exception:
                checks["adapter_import_errors"].append(module)
    print(json.dumps(checks, indent=2))
    return 0 if checks["python_supported"] and not checks["adapter_import_errors"] else 1


async def _demo() -> int:
    driver = _DemoDriver()
    engine = _DemoEngine()
    result = await ComputerUseRunner(driver, engine, engine).run("type Hello")
    print(json.dumps(result.as_dict(), indent=2))
    return 0 if result.succeeded else 1


async def _real_run(goal: str, output: str | None = None) -> int:
    from .adapters.aardwolf_driver import AardwolfDriver
    from .adapters.openai_vision import OpenAICompatibleVisionEngine

    config = AppConfig.from_env()
    config.require_real_run()
    driver = AardwolfDriver(
        config.rdp_host,
        config.rdp_username,
        config.rdp_password,
        domain=config.rdp_domain,
        auth=config.rdp_auth,
        port=config.rdp_port,
        width=config.width,
        height=config.height,
    )
    engine = OpenAICompatibleVisionEngine(
        config.vision_base_url,
        config.vision_model,
        config.vision_api_key,
    )
    runner = ComputerUseRunner(
        driver,
        engine,
        engine,
        RunnerConfig(
            max_steps=config.max_steps,
            action_timeout_seconds=config.action_timeout_seconds,
            repeat_action_limit=config.repeat_action_limit,
            observation_timeout_seconds=config.observation_timeout_seconds,
            model_timeout_seconds=config.model_timeout_seconds,
            settle_seconds=config.settle_seconds,
        ),
    )
    try:
        await asyncio.wait_for(driver.connect(), timeout=30)
        result = await runner.run(goal)
    finally:
        try:
            await driver.disconnect()
        finally:
            await engine.close()
    payload = json.dumps(result.as_dict(), indent=2)
    if output:
        with Path(output).open("x", encoding="utf-8") as handle:
            handle.write(payload + "\n")
    print(payload)
    return 0 if result.succeeded else 1


async def _smoke_rdp(frame_timeout: float) -> int:
    from .adapters.aardwolf_driver import AardwolfDriver

    config = AppConfig.from_env()
    config.require_rdp()
    driver = AardwolfDriver(
        config.rdp_host,
        config.rdp_username,
        config.rdp_password,
        domain=config.rdp_domain,
        auth=config.rdp_auth,
        port=config.rdp_port,
        width=config.width,
        height=config.height,
    )
    try:
        await asyncio.wait_for(driver.connect(), timeout=frame_timeout)
        deadline = asyncio.get_running_loop().time() + frame_timeout
        while True:
            try:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise TimeoutError("desktop frame did not arrive")
                observation = await asyncio.wait_for(driver.capture(), timeout=remaining)
                break
            except RuntimeError:
                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError("desktop frame did not arrive")
                await asyncio.sleep(0.25)
        print(
            json.dumps(
                {
                    "status": "succeeded",
                    "frame_received": True,
                    "width": observation.width,
                    "height": observation.height,
                },
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2
    finally:
        await driver.disconnect()


def build_parser() -> argparse.ArgumentParser:
    from . import __version__
    parser = argparse.ArgumentParser(prog="rdp-cua")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor = subparsers.add_parser("doctor", help="inspect Python and optional adapters")
    doctor.add_argument("--require-adapters", action="store_true")
    subparsers.add_parser("demo", help="run the dependency-free mock loop")
    smoke_parser = subparsers.add_parser(
        "smoke-rdp",
        help="connect, receive one frame, and disconnect without sending input",
    )
    smoke_parser.add_argument("--frame-timeout", type=float, default=30.0)
    smoke_parser.add_argument("--env-file")
    run_parser = subparsers.add_parser("run", help="run one goal against configured RDP and VLM adapters")
    task = run_parser.add_mutually_exclusive_group(required=True)
    task.add_argument("--goal")
    task.add_argument("--scenario", help="JSON or Markdown scenario as model guidance")
    run_parser.add_argument("--env-file")
    run_parser.add_argument("--output", help="write result JSON to a new file; refuses overwrite")
    check = subparsers.add_parser("scenario-check", help="validate a scenario without RDP or a model")
    check.add_argument("path")
    return parser


def _dispatch(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "env_file", None):
        load_env_file(args.env_file)
    if args.command == "doctor":
        return _doctor(args.require_adapters)
    if args.command == "demo":
        return asyncio.run(_demo())
    if args.command == "smoke-rdp":
        if not math.isfinite(args.frame_timeout) or args.frame_timeout <= 0:
            raise ValueError("frame timeout must be positive")
        return asyncio.run(_smoke_rdp(args.frame_timeout))
    if args.command == "run":
        from .scenario import load_scenario
        if args.output and Path(args.output).exists():
            raise FileExistsError("output file already exists")
        if args.output and not Path(args.output).parent.is_dir():
            raise FileNotFoundError("output directory does not exist")
        goal = load_scenario(args.scenario).as_goal() if args.scenario else args.goal
        if not goal.strip():
            raise ValueError("goal cannot be empty")
        return asyncio.run(_real_run(goal, args.output))
    if args.command == "scenario-check":
        from .scenario import load_scenario
        scenario = load_scenario(args.path)
        print(json.dumps({"valid": True, "title": scenario.title, "steps": len(scenario.steps)}, indent=2))
        return 0
    raise AssertionError("unreachable")


def main(argv: list[str] | None = None) -> int:
    try:
        return _dispatch(argv)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__,
                          "hint": "Check configuration, optional adapters, file paths, and target connectivity."}), file=sys.stderr)
        return 2
