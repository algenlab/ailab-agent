"""Process validators: string."""

from __future__ import annotations

from algolab.verification.process_families.common import *
from algolab.verification.process_families.contracts import (
    _family_contract_for_trace,
    _normalize_family_contract_family,
    _normalize_family_contract_submode,
)

def _validate_kmp_prefix(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    pattern = input_data.get("pattern") or input_data.get("needle")
    if not isinstance(pattern, str):
        return errors
    expected = _kmp_prefix(pattern)
    for event in trace.events:
        state = event.state or {}
        pi = state.get("pi") or state.get("prefix") or state.get("lps") or state.get("next")
        if not isinstance(pi, list) or len(pi) != len(pattern) or not all(isinstance(x, int) for x in pi):
            continue
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind == "indexed" and parsed.name in {"pi", "prefix", "lps", "next"} and len(parsed.indices) == 1:
                i = parsed.indices[0]
                if 0 <= i < len(expected) and pi[i] != expected[i]:
                    errors.append(f"第 {event.step} 步 {parsed.name}[{i}] 不满足 KMP 前缀函数")
    return errors


def _kmp_prefix(pattern: str) -> list[int]:
    pi = [0] * len(pattern)
    j = 0
    for i in range(1, len(pattern)):
        while j and pattern[i] != pattern[j]:
            j = pi[j - 1]
        if pattern[i] == pattern[j]:
            j += 1
        pi[i] = j
    return pi


def _validate_rabin_karp_hashes(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    text = input_data.get("text") or input_data.get("haystack")
    pattern = input_data.get("pattern") or input_data.get("needle")
    if not isinstance(text, str) or not isinstance(pattern, str):
        return errors
    algorithm = (trace.algorithm or "").lower()
    if "rabin" not in algorithm and "karp" not in algorithm and "rolling" not in algorithm and "滚动哈希" not in trace.algorithm:
        return errors
    expected_pattern_hash = _string_hash(pattern)
    expected_windows = [_string_hash(text[i : i + len(pattern)]) for i in range(0, max(0, len(text) - len(pattern) + 1))]
    for event in trace.events:
        state = event.state or {}
        pattern_hash = state.get("pattern_hash")
        if isinstance(pattern_hash, int) and pattern_hash != expected_pattern_hash:
            errors.append(f"第 {event.step} 步 Rabin-Karp pattern_hash 应为 {expected_pattern_hash}")
        hashes = state.get("window_hashes") or state.get("hashes")
        if isinstance(hashes, list):
            for index, expected in enumerate(expected_windows[: len(hashes)]):
                value = hashes[index]
                if isinstance(value, int) and value != expected:
                    errors.append(f"第 {event.step} 步 Rabin-Karp window_hashes[{index}] 应为 {expected}")
            if event.op == SemanticOp.SET:
                for target in event.targets:
                    parsed = parse_target(target.id)
                    if parsed.kind == "indexed" and parsed.name in {"window_hashes", "hashes"} and len(parsed.indices) == 1:
                        i = parsed.indices[0]
                        if 0 <= i < len(expected_windows) and i < len(hashes) and isinstance(hashes[i], int) and hashes[i] != expected_windows[i]:
                            errors.append(f"第 {event.step} 步 Rabin-Karp {parsed.name}[{i}] 不满足滚动哈希")
        window_hash = state.get("window_hash")
        window_start = state.get("window_start")
        if not isinstance(window_start, int):
            window_start = _rabin_karp_window_index_from_refs(event)
        if not isinstance(window_start, int):
            window_start = state.get("i")
        if isinstance(window_hash, int) and isinstance(window_start, int) and 0 <= window_start < len(expected_windows):
            expected = expected_windows[window_start]
            if window_hash != expected:
                errors.append(f"第 {event.step} 步 Rabin-Karp window_hash 应为 {expected}")
    return errors


def _rabin_karp_window_index_from_refs(event) -> int | None:
    for refs in (_event_target_ids(event), _event_dep_ids(event)):
        for ref in sorted(refs):
            parsed = parse_target(ref)
            if parsed.kind == "indexed" and parsed.name in {"window_hashes", "hashes"} and len(parsed.indices) == 1:
                index = parsed.indices[0]
                if isinstance(index, int):
                    return index
    return None


def _string_hash(value: str, *, base: int = 257, mod: int = 1_000_000_007) -> int:
    h = 0
    for ch in value:
        h = (h * base + ord(ch)) % mod
    return h


def _validate_z_algorithm(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    text = _string_input_for_algorithm(trace, state_key="text")
    if not isinstance(text, str):
        return errors
    algorithm = (trace.algorithm or "").lower()
    has_z_signal = "z algorithm" in algorithm or "z 算法" in trace.algorithm or any("z" in (event.state or {}) for event in trace.events)
    if not has_z_signal:
        return errors
    expected = _z_values(text)
    for event in trace.events:
        z = (event.state or {}).get("z")
        if not isinstance(z, list) or len(z) != len(text) or not all(isinstance(x, int) for x in z):
            continue
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind == "indexed" and parsed.name == "z" and len(parsed.indices) == 1:
                i = parsed.indices[0]
                if 0 <= i < len(expected) and z[i] != expected[i]:
                    errors.append(f"第 {event.step} 步 Z Algorithm z[{i}] 应为 {expected[i]}")
    return errors


def _string_input_for_algorithm(trace: SemanticTrace, *, state_key: str) -> str | None:
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    value = input_data.get(state_key) or input_data.get("s") or input_data.get("string")
    if isinstance(value, str):
        return value
    for event in trace.events:
        state_value = (event.state or {}).get(state_key)
        if isinstance(state_value, str):
            return state_value
    return None


def _z_values(text: str) -> list[int]:
    n = len(text)
    z = [0] * n
    left = right = 0
    for i in range(1, n):
        if i <= right:
            z[i] = min(right - i + 1, z[i - left])
        while i + z[i] < n and text[z[i]] == text[i + z[i]]:
            z[i] += 1
        if i + z[i] - 1 > right:
            left, right = i, i + z[i] - 1
    return z


def _validate_manacher_radius(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    algorithm = (trace.algorithm or "").lower()
    has_signal = "manacher" in algorithm or "回文半径" in trace.algorithm or any("radius" in (event.state or {}) for event in trace.events)
    if not has_signal:
        return errors
    raw_text = _string_input_for_algorithm(trace, state_key="text")
    if not isinstance(raw_text, str):
        return errors
    expected_by_text = {
        raw_text: _manacher_radius(raw_text) if _looks_transformed_manacher_text(raw_text) else _odd_palindrome_radius(raw_text),
    }
    transformed = _manacher_transform(raw_text)
    expected_by_text.setdefault(transformed, _manacher_radius(transformed))
    for event in trace.events:
        state = event.state or {}
        state_text = state.get("text")
        radius = state.get("radius") or state.get("p")
        if not isinstance(state_text, str) or not isinstance(radius, list) or not all(isinstance(x, int) for x in radius):
            continue
        expected = expected_by_text.get(state_text)
        if expected is None and _looks_transformed_manacher_text(state_text):
            expected = _manacher_radius(state_text)
        if expected is None or len(radius) != len(expected):
            continue
        if event.op != SemanticOp.SET:
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind == "indexed" and parsed.name in {"radius", "p"} and len(parsed.indices) == 1:
                i = parsed.indices[0]
                if 0 <= i < len(expected) and radius[i] != expected[i]:
                    errors.append(f"第 {event.step} 步 Manacher {parsed.name}[{i}] 应为 {expected[i]}")
    return errors


def _validate_string_sliding_window(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    contract = _family_contract_for_trace(trace)
    if not _string_contract_submode_is(contract, {"string_sliding_window", "sliding_window", "window"}):
        return errors
    previous: tuple[int, int] | None = None
    seen_window_event = False
    for event in trace.events:
        state = event.state or {}
        text = state.get("text") or _string_input_for_algorithm(trace, state_key="text")
        left = state.get("left", state.get("window_start"))
        right = state.get("right", state.get("window_end"))
        if not isinstance(text, str) or not isinstance(left, int) or not isinstance(right, int):
            continue
        seen_window_event = True
        if left < 0 or right < -1 or left > len(text) or right >= len(text):
            errors.append(f"第 {event.step} 步字符串滑动窗口指针越界")
        if previous is not None:
            prev_left, prev_right = previous
            if abs(left - prev_left) > 1 or abs(right - prev_right) > 1:
                errors.append(f"第 {event.step} 步字符串滑动窗口指针跳变")
        previous = (left, right)
        counts = state.get("window_counts") or state.get("count")
        if isinstance(counts, dict):
            expected_counts = _char_counts(text[left : right + 1] if left <= right else "")
            normalized_counts = {str(key): value for key, value in counts.items() if isinstance(value, int)}
            if normalized_counts != expected_counts:
                errors.append(f"第 {event.step} 步字符串滑动窗口 window_counts 应为 {expected_counts}")
            if any(value > 1 for value in normalized_counts.values()) and not _string_window_event_allows_duplicate_before_shrink(event):
                errors.append(f"第 {event.step} 步字符串滑动窗口包含重复字符")
        best = state.get("best")
        if isinstance(best, int) and best < 0:
            errors.append(f"第 {event.step} 步字符串滑动窗口 best 不能为负数")
        if event.op in {SemanticOp.MOVE, SemanticOp.SET, SemanticOp.MARK}:
            if not _event_refs_include_prefix(event, ("text[", "pointer:")):
                errors.append(f"第 {event.step} 步字符串滑动窗口缺少 text 或 pointer target")
    if not seen_window_event:
        errors.append("字符串滑动窗口缺少 left/right 窗口状态")
    return errors


def _string_window_event_allows_duplicate_before_shrink(event) -> bool:
    if event.op == SemanticOp.MOVE and "pointer:right" in _event_target_ids(event):
        return True
    state = event.state or {}
    text = " ".join(
        str(part)
        for part in (
            event.reason,
            state.get("window_reason"),
            state.get("move_reason"),
            state.get("phase"),
        )
    ).lower()
    return any(token in text for token in ("重复", "收缩", "duplicate", "shrink", "contract"))


def _validate_trie_prefix_match(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    contract = _family_contract_for_trace(trace)
    if not _string_contract_submode_is(contract, {"trie_prefix_match", "trie_prefix", "prefix_match"}):
        return errors
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    words = input_data.get("words")
    prefix = input_data.get("prefix")
    if not isinstance(words, list) or not all(isinstance(word, str) for word in words) or not isinstance(prefix, str):
        return errors
    expected_count = sum(1 for word in words if word.startswith(prefix))
    expected_path_labels = list(prefix)
    path_labels: list[str] = []
    saw_count = False
    for event in trace.events:
        state = event.state or {}
        if "prefix_count" in state and _trie_prefix_event_is_query_step(event):
            saw_count = True
            expected_for_step = _expected_trie_prefix_count_for_event(words, prefix, event)
            if state.get("prefix_count") != expected_for_step:
                errors.append(f"第 {event.step} 步 Trie 前缀匹配 prefix_count 应为 {expected_for_step}")
        trie = state.get("trie")
        if not isinstance(trie, dict):
            continue
        labels = _trie_prefix_path_labels(trie, prefix)
        if len(labels) > len(path_labels):
            path_labels = labels
        if event.role == "answer" or state.get("answer") is not None:
            answer = state.get("answer", event.value)
            if isinstance(answer, int) and answer != expected_count:
                errors.append(f"第 {event.step} 步 Trie 前缀匹配答案应为 {expected_count}")
            if expected_count > 0 and labels != expected_path_labels:
                errors.append(f"第 {event.step} 步 Trie 前缀匹配路径应为 {expected_path_labels}")
    if expected_count > 0 and prefix and path_labels != expected_path_labels:
        errors.append(f"Trie 前缀匹配缺少完整前缀路径：{''.join(expected_path_labels)}")
    if not saw_count:
        errors.append("Trie 前缀匹配缺少 prefix_count 证据")
    return errors


def _trie_prefix_event_is_query_step(event) -> bool:
    state = event.state or {}
    if event.role == "answer" or state.get("answer") is not None:
        return True
    current = state.get("current")
    return current is not None and event.op in {SemanticOp.MARK, SemanticOp.SET}


def _expected_trie_prefix_count_for_event(words: list[str], prefix: str, event) -> int:
    state = event.state or {}
    if event.role == "answer" or state.get("answer") is not None:
        partial = prefix
    else:
        index = state.get("i")
        partial = prefix[: index + 1] if isinstance(index, int) and index >= 0 else prefix
    return sum(1 for word in words if word.startswith(partial))


def _string_contract_submode_is(contract: dict[str, Any] | None, expected: set[str]) -> bool:
    if not isinstance(contract, dict):
        return False
    if _normalize_family_contract_family(contract.get("family") or contract.get("submode")) != "string":
        return False
    return _normalize_family_contract_submode(contract) in expected


def _char_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    return counts


def _trie_prefix_path_labels(trie: dict[str, Any], prefix: str) -> list[str]:
    nodes = trie.get("nodes")
    edges = trie.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return []
    labels = {
        str(node.get("id")): str(node.get("label", ""))
        for node in nodes
        if isinstance(node, dict) and node.get("id") is not None
    }
    children: dict[str, list[str]] = {}
    for edge in edges:
        if isinstance(edge, (list, tuple)) and len(edge) >= 2:
            children.setdefault(str(edge[0]), []).append(str(edge[1]))
    current = "root"
    path: list[str] = []
    for ch in prefix:
        next_id = None
        for candidate in children.get(current, []):
            if labels.get(candidate) == ch:
                next_id = candidate
                break
        if next_id is None:
            return path
        path.append(ch)
        current = next_id
    return path


def _looks_transformed_manacher_text(text: str) -> bool:
    return len(text) % 2 == 1 and all((i % 2 == 0) == (ch == "#") for i, ch in enumerate(text))


def _manacher_transform(text: str) -> str:
    return "#" + "#".join(text) + "#"


def _manacher_radius(text: str) -> list[int]:
    radius = [0] * len(text)
    center = right = 0
    for i in range(len(text)):
        mirror = 2 * center - i
        if i < right and 0 <= mirror < len(text):
            radius[i] = min(right - i, radius[mirror])
        while i - radius[i] - 1 >= 0 and i + radius[i] + 1 < len(text) and text[i - radius[i] - 1] == text[i + radius[i] + 1]:
            radius[i] += 1
        if i + radius[i] > right:
            center, right = i, i + radius[i]
    return radius


def _odd_palindrome_radius(text: str) -> list[int]:
    radius = [0] * len(text)
    left = 0
    right = -1
    for i in range(len(text)):
        k = 1 if i > right else min(radius[left + right - i], right - i + 1)
        while i - k >= 0 and i + k < len(text) and text[i - k] == text[i + k]:
            k += 1
        radius[i] = k
        if i + k - 1 > right:
            left, right = i - k + 1, i + k - 1
    return radius

__all__ = [name for name in globals() if not name.startswith("__")]
