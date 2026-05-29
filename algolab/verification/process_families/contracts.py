"""Process validators: contracts."""

from __future__ import annotations

from algolab.verification.process_families.common import *

def _validate_family_trace_contract(trace: SemanticTrace) -> list[str]:
    contract = _family_contract_for_trace(trace)
    if contract is None:
        return []
    family = _normalize_family_contract_family(contract.get("family") or contract.get("submode"))
    if not family:
        return ["Family contract 缺少 family，无法选择算法族过程合同"]
    if family not in FAMILY_CONTRACT_FAMILIES:
        return [f"Family contract 未支持的 family：{family}"]
    if family == "string":
        return _validate_family_contract_string(trace, contract)
    if family == "tree":
        return _validate_family_contract_tree(trace, contract)
    if family == "backtracking":
        return _validate_family_contract_backtracking(trace, contract)
    if family == "heap":
        return _validate_family_contract_heap(trace, contract)
    if family == "trie":
        return _validate_family_contract_trie(trace, contract)
    if family == "linked_list":
        return _validate_family_contract_linked_list(trace, contract)
    return []


def _family_contract_for_trace(trace: SemanticTrace) -> dict[str, Any] | None:
    for event in trace.events:
        contract = (event.state or {}).get("family_contract")
        if isinstance(contract, dict):
            return contract
    return None


def _normalize_family_contract_family(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_").replace("/", "_")
    aliases = {
        "strings": "string",
        "字符串": "string",
        "kmp": "string",
        "rabin_karp": "string",
        "z_algorithm": "string",
        "manacher": "string",
        "trees": "tree",
        "binary_tree": "tree",
        "树": "tree",
        "二叉树": "tree",
        "recursion": "backtracking",
        "回溯": "backtracking",
        "递归": "backtracking",
        "permutation": "backtracking",
        "permutations": "backtracking",
        "priority_queue": "heap",
        "堆": "heap",
        "trie_prefix": "trie",
        "前缀树": "trie",
        "linkedlist": "linked_list",
        "linked_list_reverse": "linked_list",
        "linked": "linked_list",
        "链表": "linked_list",
    }
    return aliases.get(normalized, normalized)


def _family_contract_string_list(contract: dict[str, Any], key: str) -> list[str]:
    raw = contract.get(key)
    if not isinstance(raw, list):
        return []
    return [item.strip() for item in raw if isinstance(item, str) and item.strip()]


def _validate_family_contract_string(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_tables = _family_contract_string_list(contract, "expected_tables")
    if not expected_tables:
        expected_tables = ["pi"] if _normalize_family_contract_submode(contract) == "kmp" else []
    if not any(_state_has_string_pointer_pair(event.state or {}) for event in trace.events):
        errors.append("Family contract string 缺少 text/pattern 指针")
    if expected_tables and not any(any(table in (event.state or {}) for table in expected_tables) for event in trace.events):
        errors.append(f"Family contract string 缺少表结构：{', '.join(expected_tables)}")
    elif not expected_tables and not any(_state_has_any(event.state or {}, ("pi", "prefix", "lps", "next", "z", "radius", "p", "hash", "hashes", "window_hash", "window_hashes", "count", "window_counts")) for event in trace.events):
        errors.append("Family contract string 缺少表结构")
    if not _trace_has_string_reason_event(trace, contract):
        errors.append("Family contract string 缺少失配/扩展或窗口移动原因")
    if not any(_event_refs_include_prefix(event, ("text[", "pattern[")) for event in trace.events):
        errors.append("Family contract string 缺少 text[i] / pattern[j] 字符 target")
    errors.extend(_validate_family_contract_expected_events(trace, contract, "string"))
    return errors


def _normalize_family_contract_submode(contract: dict[str, Any]) -> str:
    value = contract.get("submode")
    return value.strip().lower().replace("-", "_").replace(" ", "_") if isinstance(value, str) else ""


def _state_has_string_pointer_pair(state: dict[str, Any]) -> bool:
    has_text = isinstance(state.get("text"), str)
    has_pattern = isinstance(state.get("pattern"), str)
    has_text_pointer = any(isinstance(state.get(key), int) for key in ("i", "text_index", "text_pos", "window_start"))
    has_pattern_pointer = any(isinstance(state.get(key), int) for key in ("j", "pattern_index", "pattern_pos"))
    return has_text and has_pattern and has_text_pointer and has_pattern_pointer


def _trace_has_string_reason_event(trace: SemanticTrace, contract: dict[str, Any]) -> bool:
    reason_tokens = ["失配", "回退", "扩展", "窗口", "fallback", "mismatch", "extend", "expand", "window"]
    if _normalize_family_contract_submode(contract) in {"trie_prefix_match", "trie_prefix", "prefix_match"}:
        reason_tokens.extend(["匹配", "前缀", "沿", "match", "prefix"])
    state_keys = ("fallback_reason", "mismatch_reason", "expand_reason", "extension_reason", "window_reason", "move_reason")
    for event in trace.events:
        state = event.state or {}
        reason = " ".join(str(part) for part in (event.reason, state.get("reason"), *(state.get(key, "") for key in state_keys)))
        if any(token in reason for token in reason_tokens):
            return True
    return False


def _validate_family_contract_tree(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not any(isinstance((event.state or {}).get("tree"), dict) for event in trace.events):
        errors.append("Family contract tree 缺少 tree state")
    if not any((event.state or {}).get("current") is not None for event in trace.events):
        errors.append("Family contract tree 缺少当前节点 current")
    if not _trace_has_frame_enter_exit(trace):
        errors.append("Family contract tree 缺少 enter/exit 递归 frame")
    if not any(_tree_state_has_return_value(event.state or {}) for event in trace.events):
        errors.append("Family contract tree 缺少子树返回值或聚合结果")
    missing_nodes = _family_contract_missing_targets(trace, contract, "expected_nodes", prefix="node:")
    if missing_nodes:
        errors.append(f"Family contract tree 缺少 expected_nodes 覆盖：{', '.join(missing_nodes[:6])}")
    missing_frames = _family_contract_missing_exact_refs(trace, contract, "expected_frames")
    if missing_frames:
        errors.append(f"Family contract tree 缺少 expected_frames 覆盖：{', '.join(missing_frames[:6])}")
    return errors


def _trace_has_frame_enter_exit(trace: SemanticTrace) -> bool:
    has_enter = any(event.op == SemanticOp.ENTER and any(ref.startswith("frame:") for ref in _event_target_ids(event)) for event in trace.events)
    has_exit = any(event.op == SemanticOp.EXIT and any(ref.startswith("frame:") for ref in _event_target_ids(event)) for event in trace.events)
    return has_enter and has_exit


def _tree_state_has_return_value(state: dict[str, Any]) -> bool:
    return any(
        key in state and state.get(key) not in (None, {}, [])
        for key in ("return_values", "return_value", "subtree_return", "aggregate", "height", "diameter", "dp_take", "dp_skip")
    )


def _family_contract_missing_targets(trace: SemanticTrace, contract: dict[str, Any], key: str, *, prefix: str = "") -> list[str]:
    expected = _family_contract_string_list(contract, key)
    if not expected:
        return []
    refs = _trace_ref_ids(trace)
    missing = []
    for item in expected:
        target = item if item.startswith(prefix) else f"{prefix}{item}"
        if target not in refs:
            missing.append(item)
    return missing


def _family_contract_missing_exact_refs(trace: SemanticTrace, contract: dict[str, Any], key: str) -> list[str]:
    expected = _family_contract_string_list(contract, key)
    if not expected:
        return []
    refs = _trace_ref_ids(trace)
    return [item for item in expected if item not in refs]


def _trace_ref_ids(trace: SemanticTrace) -> set[str]:
    refs: set[str] = set()
    for event in trace.events:
        refs.update(_event_target_ids(event))
        refs.update(_event_dep_ids(event))
    return refs


def _validate_family_contract_backtracking(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not any(isinstance((event.state or {}).get("recursion_tree"), dict) or isinstance((event.state or {}).get("search_tree"), dict) for event in trace.events):
        errors.append("Family contract backtracking 缺少 recursion_tree/search_tree state")
    if not any("path" in (event.state or {}) for event in trace.events):
        errors.append("Family contract backtracking 缺少 path state")
    if _normalize_family_contract_submode(contract) in {"permutations", "permutation", "subsets", "combinations"} and not any("used" in (event.state or {}) for event in trace.events):
        errors.append("Family contract backtracking 缺少 used state")
    if not _trace_has_backtracking_choose(trace):
        errors.append("Family contract backtracking 缺少 choose 事件")
    if not _trace_has_backtracking_record(trace):
        errors.append("Family contract backtracking 缺少 record 事件")
    if not _trace_has_backtracking_undo(trace):
        errors.append("Family contract backtracking 缺少 undo 事件")
    errors.extend(_validate_backtracking_state_continuity(trace))
    errors.extend(_validate_family_contract_expected_events(trace, contract, "backtracking"))
    return errors


def _trace_has_backtracking_choose(trace: SemanticTrace) -> bool:
    return any(
        event.op in {SemanticOp.PUSH, SemanticOp.MARK, SemanticOp.SET, SemanticOp.ENTER}
        and _event_has_role_or_reason(event, ("choose", "选择"))
        for event in trace.events
    )


def _trace_has_backtracking_record(trace: SemanticTrace) -> bool:
    return any(
        (event.role == "answer" or _event_has_role_or_reason(event, ("record", "记录")))
        and "answer" in (event.state or {})
        for event in trace.events
    )


def _trace_has_backtracking_undo(trace: SemanticTrace) -> bool:
    return any(
        event.op in {SemanticOp.POP, SemanticOp.UNMARK, SemanticOp.EXIT, SemanticOp.SET}
        and _event_has_role_or_reason(event, ("undo", "撤销", "回溯"))
        for event in trace.events
    )


def _event_has_role_or_reason(event, tokens: tuple[str, ...]) -> bool:
    text = " ".join(str(part) for part in (event.role, event.reason, (event.state or {}).get("action"), (event.state or {}).get("phase")))
    lowered = text.lower()
    return any(token.lower() in lowered for token in tokens)


def _validate_backtracking_state_continuity(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    previous_path: list[Any] | None = None
    previous_used: list[Any] | None = None
    for event in trace.events:
        state = event.state or {}
        path = state.get("path")
        used = state.get("used")
        if isinstance(path, list) and previous_path is not None and abs(len(path) - len(previous_path)) > 1:
            errors.append(f"第 {event.step} 步 Family contract backtracking path 跳变")
        if isinstance(used, list) and previous_used is not None:
            diff = sum(1 for left, right in zip(previous_used, used) if left != right) + abs(len(used) - len(previous_used))
            if diff > 1:
                errors.append(f"第 {event.step} 步 Family contract backtracking used 跳变")
        previous_path = path if isinstance(path, list) else previous_path
        previous_used = used if isinstance(used, list) else previous_used
    return errors


def _validate_family_contract_heap(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    heap_events = [event for event in trace.events if isinstance((event.state or {}).get("heap"), list)]
    if not heap_events:
        errors.append("Family contract heap 缺少 heap state")
        return errors
    if not any(event.op == SemanticOp.PUSH for event in heap_events):
        errors.append("Family contract heap 缺少 push 事件")
    if "pop" in _family_contract_string_list(contract, "expected_events") and not any(event.op == SemanticOp.POP for event in heap_events):
        errors.append("Family contract heap 缺少 pop 事件")
    if not any("heap_top" in (event.state or {}) or _has_heap_zero_target(event) for event in heap_events if (event.state or {}).get("heap")):
        errors.append("Family contract heap 缺少 heap_top 或 heap[0] 证据")
    for event in heap_events:
        heap = (event.state or {}).get("heap")
        if isinstance(heap, list) and heap:
            top = (event.state or {}).get("heap_top")
            if top is not None and heap[0] != top:
                errors.append(f"第 {event.step} 步 Family contract heap heap_top 应等于 heap[0]")
    errors.extend(_validate_family_contract_expected_events(trace, contract, "heap"))
    return errors


def _has_heap_zero_target(event) -> bool:
    return "heap[0]" in (_event_target_ids(event) | _event_dep_ids(event))


def _validate_family_contract_trie(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    trie_events = [event for event in trace.events if isinstance((event.state or {}).get("trie"), dict)]
    if not trie_events:
        errors.append("Family contract trie 缺少 trie state")
        return errors
    if not any(event.op in {SemanticOp.LINK, SemanticOp.SET, SemanticOp.MARK} and any(ref.startswith("node:") for ref in _event_target_ids(event)) for event in trie_events):
        errors.append("Family contract trie 缺少字符路径节点创建/访问事件")
    if not any(_trie_state_has_terminal(event.state or {}) for event in trie_events):
        errors.append("Family contract trie 缺少 terminal 标记")
    if not any(_trie_state_has_count(event.state or {}) for event in trie_events):
        errors.append("Family contract trie 缺少 count / prefix_count 证据")
    if not any(_trie_state_has_char_signal(event.state or {}) or _event_refs_include_prefix(event, ("text[", "pattern[", "words[")) for event in trie_events):
        errors.append("Family contract trie 缺少字符路径证据")
    errors.extend(_validate_family_contract_expected_events(trace, contract, "trie"))
    return errors


def _trie_state_has_terminal(state: dict[str, Any]) -> bool:
    trie = state.get("trie")
    if not isinstance(trie, dict):
        return False
    for node in trie.get("nodes") or []:
        if isinstance(node, dict):
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            if node.get("terminal") is True or meta.get("terminal") is True or meta.get("is_word") is True:
                return True
    return False


def _trie_state_has_count(state: dict[str, Any]) -> bool:
    if any(key in state for key in ("count", "prefix_count", "terminal_count")):
        return True
    trie = state.get("trie")
    if not isinstance(trie, dict):
        return False
    for node in trie.get("nodes") or []:
        if isinstance(node, dict):
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            if any(key in node for key in ("count", "prefix_count")) or any(key in meta for key in ("count", "prefix_count", "pass_count")):
                return True
    return False


def _trie_state_has_char_signal(state: dict[str, Any]) -> bool:
    return any(isinstance(state.get(key), str) and state.get(key) for key in ("char", "current_char", "ch"))


def _validate_family_contract_linked_list(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    linked_events = [event for event in trace.events if isinstance((event.state or {}).get("linked_list"), dict)]
    if not linked_events:
        errors.append("Family contract linked_list 缺少 linked_list state")
        return errors
    max_node_count = max((_linked_node_count(event.state or {}) for event in linked_events), default=0)
    if not any(_linked_state_has_pointer(event.state or {}) or _event_refs_include_prefix(event, ("pointer:",)) for event in linked_events):
        errors.append("Family contract linked_list 缺少 pointer/current/prev/next 证据")
    if max_node_count > 1 and not any(event.op in {SemanticOp.LINK, SemanticOp.UNLINK, SemanticOp.SET} and _event_refs_include_prefix(event, ("edge:",)) for event in linked_events):
        errors.append("Family contract linked_list 缺少 next/prev 改变事件")
    if not any(_linked_state_has_next_prev(event.state or {}) for event in linked_events):
        errors.append("Family contract linked_list 缺少 next/prev 状态")
    linked_contract = dict(contract)
    if max_node_count <= 1:
        expected_events = [event for event in _family_contract_string_list(contract, "expected_events") if event != "link_change"]
        if max_node_count == 0:
            expected_events = [event for event in expected_events if event != "move_pointer"]
        linked_contract["expected_events"] = expected_events
    errors.extend(_validate_family_contract_expected_events(trace, linked_contract, "linked_list"))
    return errors


def _linked_node_count(state: dict[str, Any]) -> int:
    linked = state.get("linked_list")
    if not isinstance(linked, dict):
        return 0
    nodes = linked.get("nodes")
    return len(nodes) if isinstance(nodes, list) else 0


def _linked_state_has_pointer(state: dict[str, Any]) -> bool:
    return any(key in state for key in ("current", "prev", "next", "head", "tail"))


def _linked_state_has_next_prev(state: dict[str, Any]) -> bool:
    if any(key in state for key in ("next", "prev")):
        return True
    linked = state.get("linked_list")
    if not isinstance(linked, dict):
        return False
    for node in linked.get("nodes") or []:
        if isinstance(node, dict):
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            if any(key in node for key in ("next", "prev")) or any(key in meta for key in ("next", "prev")):
                return True
    return False


def _validate_family_contract_expected_events(trace: SemanticTrace, contract: dict[str, Any], family: str) -> list[str]:
    errors: list[str] = []
    expected = _family_contract_string_list(contract, "expected_events")
    if not expected:
        return errors
    present = _family_contract_present_event_tokens(trace)
    missing = [token for token in expected if token not in present]
    if missing:
        errors.append(f"Family contract {family} 缺少关键事件：{', '.join(missing[:6])}")
    return errors


def _family_contract_present_event_tokens(trace: SemanticTrace) -> set[str]:
    tokens: set[str] = set()
    for event in trace.events:
        tokens.add(event.op.value)
        text = " ".join(str(part) for part in (event.role, event.reason, (event.state or {}).get("action"), (event.state or {}).get("phase"))).lower()
        mapping = {
            "choose": ("choose", "选择"),
            "record": ("record", "记录", "答案"),
            "undo": ("undo", "撤销", "回溯"),
            "compare": ("compare", "比较"),
            "fallback": ("fallback", "回退", "失配"),
            "create_node": ("create_node", "创建", "新节点"),
            "terminal": ("terminal", "is_word", "单词结束"),
            "prefix_count": ("prefix_count", "count", "计数"),
            "move_pointer": ("move_pointer", "移动", "pointer"),
            "link_change": ("link_change", "next", "prev", "指针"),
        }
        for token, needles in mapping.items():
            if any(needle in text for needle in needles):
                tokens.add(token)
        if event.op == SemanticOp.LINK and any(ref.startswith("node:") for ref in _event_target_ids(event)):
            tokens.add("create_node")
        if event.op in {SemanticOp.LINK, SemanticOp.UNLINK} and any(ref.startswith("edge:") for ref in _event_target_ids(event)):
            tokens.add("link_change")
        if event.op == SemanticOp.MOVE and any(ref.startswith("pointer:") for ref in _event_target_ids(event)):
            tokens.add("move_pointer")
        state = event.state or {}
        if _trie_state_has_terminal(state):
            tokens.add("terminal")
        if _trie_state_has_count(state):
            tokens.add("prefix_count")
    return tokens

__all__ = [name for name in globals() if not name.startswith("__")]
