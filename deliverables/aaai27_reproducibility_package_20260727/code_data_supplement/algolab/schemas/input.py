"""Input schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProblemInput(BaseModel):
    """User-facing request for one algorithm visualization artifact."""

    model_config = ConfigDict(extra="forbid")

    problem: str = Field(description="LeetCode 风格题目描述")
    input_data: Any = Field(description="本次可视化使用的具体 JSON 输入")
    strategy_hint: str = Field(default="", description="可选：指定解法思路，例如动态规划")
    user_code: str = Field(default="", description="可选：用户提供的解法代码")
    expected_result: Any | None = Field(default=None, description="可选：期望输出，用于强校验")
    solution_count: int = Field(default=2, ge=1, le=4, description="希望生成的解法数量")
    teaching_enrichment: bool = Field(default=False, description="是否在 trace 校验后调用 LLM 生成讲解和交互增强")
    case_id: str = Field(default="", description="内部评测 case id，用于结果等价归一化；不暴露给 LLM prompt")
    family_id: str = Field(default="", description="内部评测 family id，用于结果等价归一化；不暴露给 LLM prompt")
    subfamily_id: str = Field(default="", description="内部评测 subfamily id，用于结果等价归一化；不暴露给 LLM prompt")
    prompt_profile: Literal["hybrid_current", "service_only"] = Field(
        default="hybrid_current",
        description="内部实验提示词配置；不写入用户题面。",
    )
    execution_mode: Literal["atomic", "decoupled"] = Field(
        default="atomic",
        description="内部执行实验条件；两种模式均从一次 instrumented trace 执行产生结果和轨迹。",
    )
    output_language: Literal["zh", "en"] = Field(
        default="zh",
        description="生成产物的人类可读语言；en 要求 UI、讲解、反馈、日志和代码注释全部为英文",
    )

    @field_validator("execution_mode", mode="before")
    @classmethod
    def normalize_legacy_execution_mode(cls, value: Any) -> Any:
        # Older benchmark entry points still pass ``separate`` explicitly.
        return "atomic" if value == "separate" else value
