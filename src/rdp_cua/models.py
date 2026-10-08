from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Mapping


class ActionKind(str, Enum):
    LEFT_CLICK = "left_click"
    RIGHT_CLICK = "right_click"
    DOUBLE_CLICK = "double_click"
    TYPE = "type"
    KEY = "key"
    SCROLL = "scroll"
    WAIT = "wait"


class TaskStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    MAX_STEPS = "max_steps"


@dataclass(frozen=True, slots=True)
class Action:
    kind: ActionKind
    coordinate: tuple[int, int] | None = None
    text: str | None = None
    key: str | None = None
    seconds: float | None = None
    scroll_delta: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ActionKind):
            raise ValueError("kind must be an ActionKind")
        if self.coordinate is not None:
            if not isinstance(self.coordinate, (tuple, list)) or len(self.coordinate) != 2:
                raise ValueError("coordinate must contain two integers")
            if any(type(n) is not int or not 0 <= n <= 1000 for n in self.coordinate):
                raise ValueError("coordinate values must be integers within 0..1000")
            object.__setattr__(self, "coordinate", tuple(self.coordinate))
        if self.text is not None and (not isinstance(self.text, str) or len(self.text) > 10000):
            raise ValueError("text must be a string of at most 10000 characters")
        if self.key is not None and (not isinstance(self.key, str) or not self.key.strip()):
            raise ValueError("key must be a non-empty string")
        if self.seconds is not None and (type(self.seconds) not in (int, float) or not math.isfinite(self.seconds) or not 0 <= self.seconds <= 300):
            raise ValueError("seconds must be finite and within 0..300")
        if self.scroll_delta is not None and (type(self.scroll_delta) is not int or not 1 <= abs(self.scroll_delta) <= 20):
            raise ValueError("scroll_delta must be a nonzero integer within -20..20")
        allowed = {
            ActionKind.LEFT_CLICK: {"coordinate"}, ActionKind.RIGHT_CLICK: {"coordinate"},
            ActionKind.DOUBLE_CLICK: {"coordinate"}, ActionKind.TYPE: {"text"},
            ActionKind.KEY: {"key"}, ActionKind.WAIT: {"seconds"},
            ActionKind.SCROLL: {"scroll_delta", "coordinate"},
        }[self.kind]
        for name in ("coordinate", "text", "key", "seconds", "scroll_delta"):
            if getattr(self, name) is not None and name not in allowed:
                raise ValueError("action contains fields for another action kind")
        if self.kind in {ActionKind.LEFT_CLICK, ActionKind.RIGHT_CLICK, ActionKind.DOUBLE_CLICK}:
            if self.coordinate is None or len(self.coordinate) != 2:
                raise ValueError(f"{self.kind.value} requires a coordinate")
            x, y = self.coordinate
            if not (0 <= x <= 1000 and 0 <= y <= 1000):
                raise ValueError("normalized coordinates must be within 0..1000")
        if self.kind is ActionKind.TYPE and self.text is None:
            raise ValueError("type requires text")
        if self.kind is ActionKind.KEY and not self.key:
            raise ValueError("key requires a key name")
        if self.kind is ActionKind.WAIT and (self.seconds is None or self.seconds < 0):
            raise ValueError("wait requires non-negative seconds")
        if self.kind is ActionKind.SCROLL and self.scroll_delta is None:
            raise ValueError("scroll requires scroll_delta")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Action":
        if not isinstance(value, Mapping) or "kind" not in value:
            raise ValueError("action requires a kind")
        if set(value) - {"kind", "coordinate", "text", "key", "seconds", "scroll_delta"}:
            raise ValueError("action contains unknown fields")
        raw_coordinate = value.get("coordinate")
        coordinate = None
        if raw_coordinate is not None:
            if not isinstance(raw_coordinate, (list, tuple)) or len(raw_coordinate) != 2:
                raise ValueError("coordinate must contain exactly two integers")
            coordinate = tuple(raw_coordinate)
        return cls(
            kind=ActionKind(str(value["kind"])),
            coordinate=coordinate,
            text=value.get("text"),
            key=value.get("key"),
            seconds=value.get("seconds"),
            scroll_delta=value.get("scroll_delta"),
        )

    def fingerprint(self) -> tuple[Any, ...]:
        return (
            self.kind.value,
            self.coordinate,
            self.text,
            self.key,
            self.seconds,
            self.scroll_delta,
        )


@dataclass(frozen=True, slots=True)
class Observation:
    image_png: bytes = field(repr=False)
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("observation dimensions must be positive")
        if not self.image_png:
            raise ValueError("observation image cannot be empty")


@dataclass(frozen=True, slots=True)
class Decision:
    completed: bool
    reason: str
    action: Action | None = None

    def __post_init__(self) -> None:
        if type(self.completed) is not bool or not isinstance(self.reason, str):
            raise ValueError("decision requires a boolean completed and string reason")
        if self.action is not None and not isinstance(self.action, Action):
            raise ValueError("decision action must be an Action")
        if self.completed and self.action is not None:
            raise ValueError("a completed decision cannot include an action")
        if not self.completed and self.action is None:
            raise ValueError("an incomplete decision requires one action")


@dataclass(frozen=True, slots=True)
class Verification:
    action_succeeded: bool
    goal_completed: bool
    summary: str

    def __post_init__(self) -> None:
        if type(self.action_succeeded) is not bool or type(self.goal_completed) is not bool:
            raise ValueError("verification flags must be JSON booleans")
        if not isinstance(self.summary, str):
            raise ValueError("verification summary must be a string")


@dataclass(frozen=True, slots=True)
class StepRecord:
    number: int
    action: Action
    decision_reason: str
    verification: Verification


@dataclass(frozen=True, slots=True)
class TaskResult:
    status: TaskStatus
    reason: str
    steps: tuple[StepRecord, ...]

    @property
    def succeeded(self) -> bool:
        return self.status is TaskStatus.SUCCEEDED

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "step_count": len(self.steps),
            "steps": [
                {
                    "number": step.number,
                    "action": step.action.kind.value,
                    "decision_reason": step.decision_reason,
                    "action_succeeded": step.verification.action_succeeded,
                    "goal_completed": step.verification.goal_completed,
                    "verification": step.verification.summary,
                }
                for step in self.steps
            ],
        }
