"""Correctness contract schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator


class InputSchema(RootModel[dict[str, str]]):
    """Minimal named-field input type expression."""

    @field_validator("root")
    @classmethod
    def fields_are_non_empty(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("input_schema must define at least one field")
        cleaned: dict[str, str] = {}
        for name, type_expr in value.items():
            field_name = name.strip()
            field_type = type_expr.strip()
            if not field_name:
                raise ValueError("input_schema field names must be non-empty")
            if not field_type:
                raise ValueError(f"input_schema field {field_name!r} must define a type")
            cleaned[field_name] = field_type
        return cleaned


class OutputSchema(RootModel[str]):
    """Minimal output type expression."""

    @field_validator("root")
    @classmethod
    def expression_is_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("output_schema must be non-empty")
        return value


class Postcondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expression: str
    severity: Literal["blocking", "warning"] = "blocking"

    @model_validator(mode="before")
    @classmethod
    def accept_plain_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"expression": value}
        return value

    @field_validator("expression")
    @classmethod
    def expression_is_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("postcondition expression must be non-empty")
        return value


class OracleStrategy(str, Enum):
    NONE = "none"
    EXPECTED_ONLY = "expected_only"
    BRUTE_FORCE = "brute_force"
    USER_PROVIDED = "user_provided"
    GENERATED_VERIFIER = "generated_verifier"


class ContractTestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: Any
    expected: Any = None
    name: str = ""
    note: str = ""


class MetamorphicRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str

    @model_validator(mode="before")
    @classmethod
    def accept_plain_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"description": value}
        return value

    @field_validator("description")
    @classmethod
    def description_is_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("metamorphic relation must be non-empty")
        return value


class ContractReleaseGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_ready: bool = False
    schema_ready: bool = False
    oracle_ready: bool = False
    expected_consistent: bool = False
    generated_tests_pass: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)


class ContractValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["contract-validation-report-v1"] = "contract-validation-report-v1"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    release_gate: ContractReleaseGate = Field(default_factory=ContractReleaseGate)


class CorrectnessContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["correctness-contract-v1"] = "correctness-contract-v1"
    input_schema: InputSchema
    output_schema: OutputSchema
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[Postcondition] = Field(min_length=1)
    oracle_strategy: OracleStrategy = OracleStrategy.NONE
    oracle_code: str = ""
    test_cases: list[ContractTestCase] = Field(default_factory=list)
    metamorphic_relations: list[MetamorphicRelation] = Field(default_factory=list)
    process_invariants: list[str] = Field(default_factory=list)

    @field_validator("preconditions", "process_invariants")
    @classmethod
    def text_items_are_non_empty(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("text list entries must be non-empty")
        return cleaned
