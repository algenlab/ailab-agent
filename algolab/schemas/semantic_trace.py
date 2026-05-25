"""Semantic trace schemas.

The trace language is intentionally small. New algorithms should normally map
to these operations instead of adding algorithm-specific op names.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SemanticOp(str, Enum):
    CREATE = "create"
    SET = "set"
    MARK = "mark"
    UNMARK = "unmark"
    MOVE = "move"
    COMPARE = "compare"
    LINK = "link"
    UNLINK = "unlink"
    PUSH = "push"
    POP = "pop"
    ENTER = "enter"
    EXIT = "exit"
    EXPLAIN = "explain"


class TargetRef(BaseModel):
    """Reference to an algorithm object.

    The string form is deliberately simple:
    - nums[3]
    - dp[2][5]
    - node:A
    - edge:A->B
    - stack
    - queue
    - frame:dfs(2)
    """

    id: str = Field(description="目标引用，例如 dp[2][5] 或 node:A")
    model_config = ConfigDict(extra="forbid")

    @field_validator("id")
    @classmethod
    def non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("target id 不能为空")
        return value


class Interaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["choice", "input", "judge"] = "choice"
    prompt: str = Field(description="交互问题")
    options: list[str] = Field(default_factory=list)
    answer: Any = None
    explanation: str = ""


class TeachingStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    what: str = ""
    why: str = ""
    formula: str = ""
    invariant: str = ""
    common_mistake: str = ""
    hint: str = ""

    @field_validator("what", "why", "formula", "invariant", "common_mistake", "hint", mode="before")
    @classmethod
    def none_text_to_empty(cls, value: Any) -> Any:
        if value is None:
            return ""
        return value

    @field_validator("what", "why", "formula", "invariant", "common_mistake", "hint")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class SemanticEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=0)
    op: SemanticOp
    targets: list[TargetRef] = Field(default_factory=list)
    value: Any = None
    before: Any = None
    after: Any = None
    deps: list[TargetRef] = Field(default_factory=list)
    role: str = Field(default="", description="current/candidate/visited/answer/conflict 等通用角色")
    reason: str = Field(default="", description="这一步为什么这么做")
    state: dict[str, Any] = Field(default_factory=dict, description="关键变量快照")
    code_line: int = Field(default=1, ge=1)
    interaction: Interaction | None = None
    teaching: TeachingStep | None = None

    @field_validator("role", "reason", mode="before")
    @classmethod
    def none_text_to_empty(cls, value: Any) -> Any:
        if value is None:
            return ""
        return value


class SemanticTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "semantic-trace-v1"
    algorithm: str
    input_data: Any
    result: Any = None
    pseudocode: list[str] = Field(default_factory=list)
    events: list[SemanticEvent]

    @field_validator("events")
    @classmethod
    def events_not_empty(cls, value: list[SemanticEvent]) -> list[SemanticEvent]:
        if not value:
            raise ValueError("events 不能为空")
        return value

    @model_validator(mode="after")
    def steps_are_contiguous(self) -> "SemanticTrace":
        for i, event in enumerate(self.events):
            if event.step != i:
                raise ValueError(f"events[{i}].step 应为 {i}，实际为 {event.step}")
        return self


class SolutionVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    strategy: str
    time_complexity: str = ""
    space_complexity: str = ""
    code: str = Field(description="定义 solve(input_data) 的 Python 代码")
    tracker_code: str = Field(description="定义 trace(input_data) 的 Python 代码")
    result: Any = None
    trace: SemanticTrace | None = None
