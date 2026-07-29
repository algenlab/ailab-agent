"""Deterministic prompt profiles used by the paired Plan-2 ablation."""

from __future__ import annotations

import hashlib
from pathlib import Path


PROMPT_DIR = Path(__file__).parent / "prompts"
PROMPT_PROFILES = ("hybrid_current", "service_only")

_TRACKER_FAMILY_START = "# 高频族模板（优先按这些写，避免自造 API）"
_TRACKER_COMMON_END = "# 重要提醒"
_REPAIR_ERROR_TABLE = "# 常见错误对照"
_REPAIR_OUTPUT = "# 输出"

_NEUTRAL_SERVICE_COMPOSITION = """# 中性服务组合片段

以下片段只演示如何组合通用服务，不对应任何预置算法族，也不提供题目答案。应根据当前题目自行选择最少且足够的服务。

```python
items = sess.array("items", input_data["items"])
cursor = sess.pointer("cursor", on=items, idx=0)
summary = sess.scalar("summary", 0)
with sess.step("更新当前位置与汇总状态"):
    cursor.move(next_index)
    summary.set(next_value)
```

```python
relations = sess.graph("relations", nodes, edges, directed=directed)
frontier = sess.queue("frontier", initial_items)
status = sess.map("status", initial_status)
with sess.step("处理一个待办项"):
    current = frontier.pop()
    relations.highlight_node(current)
    status[current] = new_status
```

```python
grid = sess.table("grid", initial_rows)
choice = sess.scalar("choice", None)
with sess.step("更新一个状态单元"):
    grid[row, col] = new_value
    choice.set([row, col])
```

这些片段只说明服务接口可组合；`solve`、控制流、边界条件、最终答案与 `code_line` 必须从当前题目和输入独立推导。

"""

_SERVICE_ONLY_REPAIR_RULE = (
    "service_only 条件：只能依据当前题目、错误信息、完整 DSL API 与中性服务组合规则修复；"
    "不要引用预置算法族模板、命名算法示例或 benchmark 特例。"
)

_SPECIFIC_REPAIR_ROWS = (
    "`GraphObj` 没有 `node`",
    "Trie `trace 结果 0` 或前缀计数不一致",
    "`dictionary update sequence element` 且 Kruskal/MST",
    "`list indices must be integers or slices, not NoneType`",
    "`结果 10/19 与 expected 18` 或数位 DP 不含 7",
)


def load_profiled_prompt(name: str, prompt_profile: str = "hybrid_current") -> str:
    if prompt_profile not in PROMPT_PROFILES:
        raise ValueError(f"unknown prompt profile: {prompt_profile}")
    base = (PROMPT_DIR / name).read_text(encoding="utf-8")
    if prompt_profile == "hybrid_current":
        return base
    if name == "tracker_system.txt":
        return _service_only_tracker_prompt(base)
    if name == "repair_system.txt":
        return _service_only_repair_prompt(base)
    return base


def prompt_profile_metadata(prompt_profile: str) -> dict[str, object]:
    generation = load_profiled_prompt("tracker_system.txt", prompt_profile)
    repair = load_profiled_prompt("repair_system.txt", prompt_profile)
    return {
        "prompt_profile": prompt_profile,
        "generation_prompt_sha256": _sha256_text(generation),
        "repair_prompt_sha256": _sha256_text(repair),
        "removed_algorithm_templates": prompt_profile == "service_only",
        "strategy_hint_policy": (
            "removed" if prompt_profile == "service_only" else "benchmark_strategy"
        ),
        "profile_version": "plan2-prompt-profile-v2",
    }


def _service_only_tracker_prompt(base: str) -> str:
    family_index = base.find(_TRACKER_FAMILY_START)
    common_end_index = base.find(_TRACKER_COMMON_END)
    if family_index < 0 or common_end_index < 0 or common_end_index <= family_index:
        raise ValueError("tracker prompt markers changed; cannot build service_only profile")
    return base[:family_index] + _NEUTRAL_SERVICE_COMPOSITION + base[common_end_index:]


def _service_only_repair_prompt(base: str) -> str:
    table_index = base.find(_REPAIR_ERROR_TABLE)
    output_index = base.find(_REPAIR_OUTPUT)
    if table_index < 0 or output_index < 0 or output_index <= table_index:
        raise ValueError("repair prompt markers changed; cannot build service_only profile")
    table = base[table_index:output_index]
    neutral_table = "\n".join(
        line for line in table.splitlines() if not any(token in line for token in _SPECIFIC_REPAIR_ROWS)
    ).rstrip()
    prefix = base[:table_index].rstrip()
    suffix = base[output_index:].lstrip()
    return f"{prefix}\n\n{_SERVICE_ONLY_REPAIR_RULE}\n\n{neutral_table}\n\n{suffix}"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
