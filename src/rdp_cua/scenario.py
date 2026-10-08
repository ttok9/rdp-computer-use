from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ScenarioStep:
    number: int
    title: str
    verification: str = ""


@dataclass(frozen=True, slots=True)
class Scenario:
    title: str
    goal: str
    steps: tuple[ScenarioStep, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Scenario":
        if not isinstance(value, Mapping):
            raise ValueError("scenario must be an object")
        if any(not isinstance(value.get(key), str) for key in ("title", "goal")):
            raise ValueError("scenario title and goal must be strings")
        title = str(value.get("title", "")).strip()
        goal = str(value.get("goal", "")).strip()
        raw_steps = value.get("steps", [])
        if not title or not goal:
            raise ValueError("scenario title and goal are required")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError("scenario requires at least one step")
        for item in raw_steps:
            if not isinstance(item, Mapping) or not isinstance(item.get("title"), str):
                raise ValueError("each step requires a string title")
            if type(item.get("number", 1)) is not int or item.get("number", 1) < 1:
                raise ValueError("step numbers must be positive integers")
            if not isinstance(item.get("verification", ""), str):
                raise ValueError("step verification must be a string")
        steps = tuple(
            ScenarioStep(
                number=int(item.get("number", index)),
                title=str(item.get("title", "")).strip(),
                verification=str(item.get("verification", "")).strip(),
            )
            for index, item in enumerate(raw_steps, start=1)
        )
        if any(not step.title for step in steps):
            raise ValueError("every scenario step requires a title")
        if len({step.number for step in steps}) != len(steps):
            raise ValueError("step numbers must be unique")
        return cls(title=title, goal=goal, steps=steps)

    def as_goal(self) -> str:
        guidance = "\n".join(f"{step.number}. {step.title}. Expected: {step.verification}" for step in self.steps)
        return f"{self.goal}\nFollow this scenario guidance:\n{guidance}"


def load_scenario(path: str | Path) -> Scenario:
    if Path(path).suffix.lower() == ".md":
        return parse_markdown_scenario(Path(path).read_text(encoding="utf-8"))
    with Path(path).open("r", encoding="utf-8") as handle:
        return Scenario.from_mapping(json.load(handle))


def parse_markdown_scenario(content: str) -> Scenario:
    title = ""
    goal_lines: list[str] = []
    steps: list[ScenarioStep] = []
    section = ""
    current_number: int | None = None
    current_title = ""
    current_verification = ""

    def flush_step() -> None:
        nonlocal current_number, current_title, current_verification
        if current_number is not None:
            steps.append(ScenarioStep(current_number, current_title, current_verification))
        current_number = None
        current_title = ""
        current_verification = ""

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.lower() in {"## goal", "## 목표"}:
            section = "goal"
            continue
        if line.lower() in {"## steps", "## 단계"}:
            section = "steps"
            continue
        step_match = re.match(r"###\s+(\d+)\.\s+(.+)", line)
        if step_match:
            flush_step()
            current_number = int(step_match.group(1))
            current_title = step_match.group(2).strip()
            section = "steps"
            continue
        if section == "goal" and not line.startswith("#"):
            goal_lines.append(line)
            continue
        verification_match = re.match(
            r"-\s+\*\*(?:Verification|검증)\*\*:\s*(.+)",
            line,
            flags=re.IGNORECASE,
        )
        if verification_match and current_number is not None:
            current_verification = verification_match.group(1).strip()

    flush_step()
    return Scenario.from_mapping(
        {
            "title": title,
            "goal": " ".join(goal_lines),
            "steps": [
                {
                    "number": step.number,
                    "title": step.title,
                    "verification": step.verification,
                }
                for step in steps
            ],
        }
    )
