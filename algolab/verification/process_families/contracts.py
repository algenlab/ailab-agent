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
    if family == "union_find":
        return _validate_family_contract_union_find(trace, contract)
    if family == "monotonic_stack":
        return _validate_family_contract_monotonic_stack(trace, contract)
    if family in {"range_structure", "data_structure"}:
        if _family_contract_is_monotonic_stack_trace(trace, contract):
            return _validate_family_contract_monotonic_stack(trace, contract)
        return _validate_family_contract_range_structure(trace, contract)
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
        "monotonic_stack": "monotonic_stack",
        "daily_temperatures": "monotonic_stack",
        "每日温度": "monotonic_stack",
        "单调栈": "monotonic_stack",
        "trie_prefix": "trie",
        "前缀树": "trie",
        "linkedlist": "linked_list",
        "linked_list_reverse": "linked_list",
        "linked": "linked_list",
        "链表": "linked_list",
        "unionfind": "union_find",
        "union_find": "union_find",
        "dsu": "union_find",
        "并查集": "union_find",
        "range": "range_structure",
        "range_query": "range_structure",
        "range_structure": "range_structure",
        "segment_tree": "range_structure",
        "fenwick": "range_structure",
        "fenwick_tree": "range_structure",
        "binary_indexed_tree": "range_structure",
        "sparse_table": "range_structure",
        "data_structure": "data_structure",
        "线段树": "range_structure",
        "树状数组": "range_structure",
        "稀疏表": "range_structure",
    }
    return aliases.get(normalized, normalized)


def _family_contract_string_list(contract: dict[str, Any], key: str) -> list[str]:
    raw = contract.get(key)
    if not isinstance(raw, list):
        return []
    return [item.strip() for item in raw if isinstance(item, str) and item.strip()]


def _validate_family_contract_string(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    submode = _normalize_family_contract_submode(contract)
    if submode in {"kmp", "prefix_function"}:
        return _validate_family_contract_string_kmp(trace, contract)
    if submode in {"rabin_karp", "rolling_hash"}:
        return _validate_family_contract_string_rabin_karp(trace, contract)
    if submode in {"z_algorithm", "z"}:
        return _validate_family_contract_string_z_algorithm(trace, contract)
    if submode in {"manacher", "palindrome_radius"}:
        return _validate_family_contract_string_manacher(trace, contract)
    if submode in {"trie_prefix_match", "trie_prefix", "prefix_match"}:
        return _validate_family_contract_string_trie_prefix(trace, contract)
    if submode in {"string_sliding_window", "sliding_window", "window"}:
        return _validate_family_contract_string_sliding_window(trace, contract)
    return _validate_family_contract_string_default(trace, contract)


def _validate_family_contract_string_kmp(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors = _validate_family_contract_string_default(trace, contract, default_tables=["pi"], require_pattern=True)
    if not _trace_has_char_refs(trace, ("text[",), ("pattern[",)):
        errors.append("Family contract string kmp 缺少 text[i] / pattern[j] 字符 target")
    return errors


def _validate_family_contract_string_rabin_karp(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors = _validate_family_contract_string_default(
        trace,
        contract,
        default_tables=["pattern_hash", "window_hash"],
        require_pattern=False,
        require_generic_char_refs=False,
    )
    if not _trace_has_rabin_karp_pointer_evidence(trace):
        errors.append("Family contract string 缺少 text/pattern 指针")
    if not _trace_state_has_any_key(trace, ("pattern_hash",)):
        errors.append("Family contract string rabin_karp 缺少 pattern_hash")
    if not _trace_state_has_any_key(trace, ("window_hash", "window_hashes", "hashes")):
        errors.append("Family contract string rabin_karp 缺少 window_hash / window_hashes")
    if not _trace_has_char_refs(trace, ("text[",), ("pattern[",)):
        errors.append("Family contract string rabin_karp 缺少 text[i] / pattern[j] 字符 target")
    return errors


def _trace_has_rabin_karp_pointer_evidence(trace: SemanticTrace) -> bool:
    for event in trace.events:
        state = event.state or {}
        if not isinstance(state.get("text"), str) or not isinstance(state.get("pattern"), str):
            continue
        if _state_has_string_pointer_pair(state):
            return True
        has_text_window_pointer = any(
            isinstance(state.get(key), int)
            for key in ("i", "text_index", "text_pos", "window_start", "window_index", "start")
        )
        has_window_ref = any(
            _is_indexed_string_table_ref(ref, {"window_hashes", "hashes"})
            for ref in (*_event_target_ids(event), *_event_dep_ids(event))
        )
        has_window_hash_state = _state_has_any(state, ("window_hash", "window_hashes", "hashes"))
        has_pattern_hash_evidence = "pattern_hash" in state or "pattern_hash" in _event_target_ids(event) or "pattern_hash" in _event_dep_ids(event)
        if has_window_hash_state and has_pattern_hash_evidence and (has_text_window_pointer or has_window_ref):
            return True
    return False


def _is_indexed_string_table_ref(ref: str, names: set[str]) -> bool:
    parsed = parse_target(ref)
    return parsed.kind == "indexed" and parsed.name in names and bool(parsed.indices)


def _validate_family_contract_string_z_algorithm(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not _trace_has_text_sequence(trace):
        errors.append("Family contract string z_algorithm 缺少 text 或 s state")
    if not _trace_state_has_any_key(trace, ("z",)):
        errors.append("Family contract string z_algorithm 缺少 z 表结构")
    if not _trace_has_string_reason_event(trace, contract):
        errors.append("Family contract string z_algorithm 缺少扩展/回退原因")
    if not _trace_has_char_refs(trace, ("text[", "s[")):
        errors.append("Family contract string z_algorithm 缺少 text[i] 字符 target")
    errors.extend(_validate_family_contract_expected_tables(trace, contract))
    errors.extend(_validate_family_contract_expected_events(trace, contract, "string"))
    return errors


def _validate_family_contract_string_manacher(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not _trace_has_text_sequence(trace):
        errors.append("Family contract string manacher 缺少 text 或 s state")
    if not _trace_state_has_any_key(trace, ("radius", "p")):
        errors.append("Family contract string manacher 缺少 radius / p 表结构")
    if not _trace_has_string_reason_event(trace, contract):
        errors.append("Family contract string manacher 缺少中心扩展原因")
    if not _trace_has_char_refs(trace, ("text[", "s[")):
        errors.append("Family contract string manacher 缺少 text[i] 字符 target")
    errors.extend(_validate_family_contract_expected_tables(trace, contract))
    errors.extend(_validate_family_contract_expected_events(trace, contract, "string"))
    return errors


def _validate_family_contract_string_trie_prefix(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not any(isinstance((event.state or {}).get("trie"), dict) for event in trace.events):
        errors.append("Family contract string trie_prefix_match 缺少 trie state")
    if not any(isinstance((event.state or {}).get("prefix"), str) for event in trace.events):
        errors.append("Family contract string trie_prefix_match 缺少 prefix state")
    if not any("prefix_count" in (event.state or {}) for event in trace.events):
        errors.append("Family contract string trie_prefix_match 缺少 prefix_count 证据")
    if not _trace_has_string_reason_event(trace, contract):
        errors.append("Family contract string trie_prefix_match 缺少前缀匹配原因")
    if not any(_event_refs_include_prefix(event, ("node:", "trie")) for event in trace.events):
        errors.append("Family contract string trie_prefix_match 缺少 Trie 路径 target")
    errors.extend(_validate_family_contract_expected_events(trace, contract, "string"))
    return errors


def _validate_family_contract_string_sliding_window(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not _trace_has_text_sequence(trace):
        errors.append("Family contract string sliding_window 缺少 text 或 s state")
    if not any(_state_has_any(event.state or {}, ("left", "right", "window_start", "window_end")) for event in trace.events):
        errors.append("Family contract string sliding_window 缺少 left/right 窗口指针")
    if not any(_state_has_any(event.state or {}, ("window_counts", "count", "best", "max_len", "answer")) for event in trace.events):
        errors.append("Family contract string sliding_window 缺少 window_counts/best 证据")
    if not _trace_has_string_reason_event(trace, contract):
        errors.append("Family contract string sliding_window 缺少窗口移动原因")
    if not any(_event_refs_include_prefix(event, ("text[", "s[", "pointer:")) for event in trace.events):
        errors.append("Family contract string sliding_window 缺少 text[i] 或 pointer target")
    errors.extend(_validate_family_contract_expected_tables(trace, contract))
    errors.extend(_validate_family_contract_expected_events(trace, contract, "string"))
    return errors


def _validate_family_contract_string_default(
    trace: SemanticTrace,
    contract: dict[str, Any],
    *,
    default_tables: list[str] | None = None,
    require_pattern: bool = True,
    require_generic_char_refs: bool = True,
) -> list[str]:
    errors: list[str] = []
    expected_tables = _family_contract_string_list(contract, "expected_tables")
    if not expected_tables:
        expected_tables = list(default_tables or [])
    if require_pattern and not any(_state_has_string_pointer_pair(event.state or {}) for event in trace.events):
        errors.append("Family contract string 缺少 text/pattern 指针")
    errors.extend(_validate_family_contract_expected_tables(trace, {"expected_tables": expected_tables} if expected_tables else contract))
    if not expected_tables and not any(_state_has_any(event.state or {}, ("pi", "prefix", "lps", "next", "z", "radius", "p", "hash", "hashes", "window_hash", "window_hashes", "count", "window_counts")) for event in trace.events):
        errors.append("Family contract string 缺少表结构")
    if not _trace_has_string_reason_event(trace, contract):
        errors.append("Family contract string 缺少失配/扩展或窗口移动原因")
    if require_generic_char_refs and not any(_event_refs_include_prefix(event, ("text[", "pattern[")) for event in trace.events):
        errors.append("Family contract string 缺少 text[i] / pattern[j] 字符 target")
    errors.extend(_validate_family_contract_expected_events(trace, contract, "string"))
    return errors


def _validate_family_contract_expected_tables(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_tables = _family_contract_string_list(contract, "expected_tables")
    for table in expected_tables:
        aliases = _string_table_aliases(table)
        if not _trace_state_has_any_key(trace, aliases):
            errors.append(f"Family contract string 缺少表结构：{table}")
    return errors


def _string_table_aliases(table: str) -> tuple[str, ...]:
    normalized = table.strip()
    aliases = {
        "pi": ("pi", "prefix", "lps", "next"),
        "prefix": ("pi", "prefix", "lps", "next"),
        "lps": ("pi", "prefix", "lps", "next"),
        "next": ("pi", "prefix", "lps", "next"),
        "radius": ("radius", "p"),
        "p": ("radius", "p"),
        "window_hash": ("window_hash", "window_hashes", "hashes"),
        "window_hashes": ("window_hash", "window_hashes", "hashes"),
        "hashes": ("window_hash", "window_hashes", "hashes"),
    }
    return aliases.get(normalized, (normalized,))


def _trace_state_has_any_key(trace: SemanticTrace, keys: tuple[str, ...]) -> bool:
    return any(_state_has_any(event.state or {}, keys) for event in trace.events)


def _trace_has_text_sequence(trace: SemanticTrace) -> bool:
    return any(isinstance((event.state or {}).get(key), str) for event in trace.events for key in ("text", "s"))


def _trace_has_char_refs(trace: SemanticTrace, required: tuple[str, ...], also_required: tuple[str, ...] = ()) -> bool:
    refs = _trace_ref_ids(trace)
    return any(ref.startswith(prefix) for ref in refs for prefix in required) and all(
        any(ref.startswith(prefix) for ref in refs) for prefix in also_required
    )


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
        for key in (
            "return_values",
            "return_value",
            "subtree_return",
            "aggregate",
            "height",
            "diameter",
            "dp_take",
            "dp_skip",
            "result",
            "results",
            "order",
            "traversal",
            "inorder",
            "preorder",
            "postorder",
        )
    )


def _family_contract_missing_targets(trace: SemanticTrace, contract: dict[str, Any], key: str, *, prefix: str = "") -> list[str]:
    expected = _family_contract_string_list(contract, key)
    if not expected:
        return []
    refs = _trace_ref_ids(trace)
    if prefix == "node:":
        refs.update(f"node:{node}" for node in _trace_current_node_ids(trace))
    missing = []
    for item in expected:
        target = item if item.startswith(prefix) else f"{prefix}{item}"
        if target not in refs:
            missing.append(item)
    return missing


def _trace_current_node_ids(trace: SemanticTrace) -> set[str]:
    nodes: set[str] = set()
    for event in trace.events:
        current = (event.state or {}).get("current")
        if current is not None:
            nodes.add(str(current))
    return nodes


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
        (event.role == "answer" or _event_has_role_or_reason(event, ("record", "记录", "答案")))
        and _backtracking_state_has_record_result(event.state or {})
        for event in trace.events
    )


def _backtracking_state_has_record_result(state: dict[str, Any]) -> bool:
    for key in ("answer", "answers", "result", "results", "res", "solutions", "permutations", "output"):
        value = state.get(key)
        if value not in (None, [], {}):
            return True
    return False


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


def _validate_family_contract_union_find(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    uf_events = [
        event
        for event in trace.events
        if isinstance((event.state or {}).get("union_find"), dict) or isinstance((event.state or {}).get("dsu"), dict)
    ]
    if not uf_events:
        errors.append("Family contract union_find 缺少 union_find/dsu state")
        return errors
    if not any(isinstance(_union_find_state(event.state or {}).get("parent"), dict) for event in uf_events):
        errors.append("Family contract union_find 缺少 parent")
    if not any("rank" in _union_find_state(event.state or {}) or "size" in _union_find_state(event.state or {}) for event in uf_events):
        errors.append("Family contract union_find 缺少 rank 或 size")
    if not any(event.op in {SemanticOp.LINK, SemanticOp.SET, SemanticOp.MARK} for event in uf_events):
        errors.append("Family contract union_find 缺少 union/find 事件")
    errors.extend(_validate_family_contract_expected_events(trace, contract, "union_find"))
    return errors


def _union_find_state(state: dict[str, Any]) -> dict[str, Any]:
    raw = state.get("union_find") if isinstance(state.get("union_find"), dict) else state.get("dsu")
    return raw if isinstance(raw, dict) else {}


def _validate_family_contract_range_structure(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    range_events = [
        event
        for event in trace.events
        if any(key in (event.state or {}) for key in ("segment_tree", "bit", "fenwick", "st", "sparse_table"))
    ]
    if not range_events:
        errors.append("Family contract range_structure 缺少 segment_tree/fenwick/sparse_table state")
        return errors
    if not any(
        isinstance((event.state or {}).get("segment_tree"), dict)
        or isinstance((event.state or {}).get("bit"), list)
        or isinstance((event.state or {}).get("fenwick"), list)
        or isinstance((event.state or {}).get("st"), list)
        or isinstance((event.state or {}).get("sparse_table"), list)
        for event in range_events
    ):
        errors.append("Family contract range_structure 缺少可复核区间结构")
    errors.extend(_validate_family_contract_expected_events(trace, contract, "range_structure"))
    return errors


def _family_contract_is_monotonic_stack_trace(trace: SemanticTrace, contract: dict[str, Any]) -> bool:
    submode = _normalize_family_contract_submode(contract)
    if submode in {"monotonic_stack", "daily_temperatures", "next_greater"}:
        return True
    for event in trace.events:
        state = event.state or {}
        if (
            isinstance(state.get("stack"), list)
            and (
                state.get("stack_order") in {"increasing", "decreasing"}
                or state.get("monotonic") in {"increasing", "decreasing"}
            )
            and any(key in state for key in ("temperatures", "nums", "heights", "answer", "answers", "ans"))
        ):
            return True
    return False


def _validate_family_contract_monotonic_stack(trace: SemanticTrace, contract: dict[str, Any]) -> list[str]:
    if _family_contract_is_monotonic_stack_trace(trace, contract):
        return []
    return ["Family contract monotonic_stack 缺少 stack/answer state"]


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
            "expand": ("expand", "扩展", "中心扩展"),
            "window": ("window", "窗口"),
            "create_node": ("create_node", "创建", "新节点"),
            "terminal": ("terminal", "is_word", "单词结束"),
            "prefix_count": ("prefix_count", "count", "计数"),
            "move_pointer": ("move_pointer", "移动", "pointer"),
            "link_change": ("link_change", "next", "prev", "指针"),
            "union": ("union", "合并"),
            "find": ("find", "根"),
            "build": ("build", "构建", "初始化"),
            "update": ("update", "更新"),
            "query": ("query", "查询", "range"),
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
