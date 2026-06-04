"""Input schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProblemInput(BaseModel):
    """User-facing request for one algorithm visualization artifact."""

    model_config = ConfigDict(extra="forbid")

    problem: str = Field(description="LeetCode 风格题目描述")
    input_data: Any = Field(description="本次可视化使用的具体 JSON 输入")
    strategy_hint: str = Field(default="", description="可选：指定解法思路，例如动态规划")
    user_code: str = Field(default="", description="可选：用户提供的解法代码")
    expected_result: Any | None = Field(default=None, description="可选：期望输出，用于强校验")
    solution_count: int = Field(default=2, ge=1, le=4, description="希望生成的解法数量")
    case_id: str = Field(default="", description="内部评测 case id，用于结果等价归一化；不暴露给 LLM prompt")
    family_id: str = Field(default="", description="内部评测 family id，用于结果等价归一化；不暴露给 LLM prompt")
    subfamily_id: str = Field(default="", description="内部评测 subfamily id，用于结果等价归一化；不暴露给 LLM prompt")
