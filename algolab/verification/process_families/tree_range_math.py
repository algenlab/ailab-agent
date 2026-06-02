"""Process validators: tree range math."""

from __future__ import annotations

from algolab.verification.process_families.common import *
import math

def _looks_like_ml_training(trace: SemanticTrace) -> bool:
    algorithm = (trace.algorithm or "").lower()
    if any(token in algorithm for token in ("regression", "linear", "logistic", "gradient", "loss", "机器学习", "回归", "梯度", "训练")):
        return True
    for event in trace.events:
        if _extract_ml_state(event.state or {}) is not None:
            return True
    return False


def _validate_ml_correctness(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        ml_state = _extract_ml_state(event.state or {})
        if ml_state is None:
            continue
        tolerance = _ml_tolerance(ml_state)
        errors.extend(_validate_ml_random_seed(event.step, ml_state))
        errors.extend(_validate_ml_loss_curve(event.step, ml_state, tolerance))
        errors.extend(_validate_ml_linear_regression_step(event.step, ml_state, tolerance))
        errors.extend(_validate_ml_parameter_update(event.step, ml_state, tolerance))
    return errors


def _extract_ml_state(state: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("training", "model", "ml", "linear_regression", "logistic_regression"):
        value = state.get(key)
        if isinstance(value, dict) and _dict_has_ml_signal(value):
            return value
    if _dict_has_ml_signal(state):
        return state
    return None


def _dict_has_ml_signal(value: dict[str, Any]) -> bool:
    return any(
        key in value
        for key in (
            "features",
            "x",
            "X",
            "labels",
            "y",
            "parameters",
            "parameters_before",
            "parameters_after",
            "weights",
            "gradient",
            "gradients",
            "loss",
            "loss_curve",
            "epoch",
            "learning_rate",
            "prediction",
            "predictions",
            "decision_boundary",
            "batch",
        )
    )


def _ml_tolerance(state: dict[str, Any]) -> float:
    raw = state.get("tolerance")
    if raw is None:
        meta = state.get("ml") if isinstance(state.get("ml"), dict) else state.get("meta")
        raw = meta.get("tolerance") if isinstance(meta, dict) else None
    if isinstance(raw, (int, float)) and math.isfinite(float(raw)) and raw >= 0:
        return float(raw)
    return 1e-6


def _validate_ml_random_seed(step: int, state: dict[str, Any]) -> list[str]:
    if not _ml_uses_randomness(state):
        return []
    if _has_seed(state):
        return []
    return [f"第 {step} 步 ML 随机训练声明缺少固定 seed"]


def _ml_uses_randomness(state: dict[str, Any]) -> bool:
    random_flags = (
        state.get("randomized"),
        state.get("shuffle"),
        state.get("sample_randomly"),
        state.get("random_sampling"),
        state.get("stochastic"),
    )
    if any(flag is True for flag in random_flags):
        return True
    batch_sampling = state.get("batch_sampling") or state.get("sampling")
    if isinstance(batch_sampling, str) and batch_sampling.lower() in {"random", "shuffle", "stochastic"}:
        return True
    batch = state.get("batch")
    if isinstance(batch, dict):
        mode = batch.get("mode") or batch.get("sampling")
        if isinstance(mode, str) and mode.lower() in {"random", "shuffle", "stochastic"}:
            return True
    return False


def _has_seed(state: dict[str, Any]) -> bool:
    if state.get("seed") is not None or state.get("random_seed") is not None:
        return True
    batch = state.get("batch")
    return isinstance(batch, dict) and (batch.get("seed") is not None or batch.get("random_seed") is not None)


def _validate_ml_loss_curve(step: int, state: dict[str, Any], tolerance: float) -> list[str]:
    errors: list[str] = []
    curve = state.get("loss_curve") or state.get("loss_history")
    if curve is None:
        return errors
    if not isinstance(curve, list) or not curve:
        return [f"第 {step} 步 loss_curve 必须是非空数值序列"]
    losses: list[float] = []
    for index, value in enumerate(curve):
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            errors.append(f"第 {step} 步 loss_curve[{index}] 不是有限数值")
            continue
        loss = float(value)
        losses.append(loss)
        if loss < -tolerance:
            errors.append(f"第 {step} 步 loss_curve[{index}] 为负数")
    should_decrease = state.get("loss_should_decrease")
    if should_decrease is not False and len(losses) == len(curve):
        for index, (left, right) in enumerate(zip(losses, losses[1:]), start=1):
            if right > left + tolerance:
                errors.append(f"第 {step} 步 loss_curve[{index}] 未按容差下降")
    return errors


def _validate_ml_linear_regression_step(step: int, state: dict[str, Any], tolerance: float) -> list[str]:
    features = state.get("features", state.get("x", state.get("X")))
    labels = state.get("labels", state.get("y"))
    if not _is_numeric_vector(labels):
        return []
    rows = _as_feature_rows(features)
    if rows is None or len(rows) != len(labels):
        return []
    params = _ml_parameters(state)
    gradient = _ml_gradient(state)
    if params is None or gradient is None:
        return []
    weights = _parameter_weights(params)
    if weights is None:
        return []
    bias = _parameter_bias(params)
    predictions = _numeric_list(state.get("prediction") or state.get("predictions"))
    if predictions is None:
        predictions = [sum(weight * x for weight, x in zip(weights, row)) + bias for row in rows]
    if len(predictions) != len(labels):
        return [f"第 {step} 步 prediction 长度与标签不一致"]
    expected_weights = _linear_gradient_weights(rows, [float(y) for y in labels], predictions)
    actual_weights = _gradient_weights(gradient, len(expected_weights))
    if actual_weights is not None:
        for index, expected in enumerate(expected_weights):
            if not _close(actual_weights[index], expected, tolerance):
                errors = [f"第 {step} 步 线性回归 grad_w[{index}] 应为 {expected:.6g}，实际为 {actual_weights[index]:.6g}"]
                return errors
    expected_bias = _linear_gradient_bias([float(y) for y in labels], predictions)
    actual_bias = _gradient_bias(gradient)
    if actual_bias is not None and not _close(actual_bias, expected_bias, tolerance):
        return [f"第 {step} 步 线性回归 grad_b 应为 {expected_bias:.6g}，实际为 {actual_bias:.6g}"]
    loss = state.get("loss")
    if isinstance(loss, (int, float)) and math.isfinite(float(loss)):
        expected_loss = sum((pred - float(label)) ** 2 for pred, label in zip(predictions, labels)) / (2 * len(labels))
        if not _close(float(loss), expected_loss, tolerance):
            return [f"第 {step} 步 线性回归 loss 应为 {expected_loss:.6g}，实际为 {float(loss):.6g}"]
    return []


def _validate_ml_parameter_update(step: int, state: dict[str, Any], tolerance: float) -> list[str]:
    before = state.get("parameters_before") or state.get("before_parameters")
    after = state.get("parameters_after") or state.get("after_parameters")
    gradient = _ml_gradient(state)
    learning_rate = state.get("learning_rate") or state.get("lr")
    if not isinstance(before, dict) or not isinstance(after, dict) or gradient is None or not isinstance(learning_rate, (int, float)):
        return []
    lr = float(learning_rate)
    errors: list[str] = []
    for name, before_value in before.items():
        if name not in after:
            continue
        grad = _gradient_value_for_name(gradient, str(name))
        if grad is None:
            continue
        actual = after[name]
        if isinstance(before_value, (int, float)) and isinstance(actual, (int, float)) and isinstance(grad, (int, float)):
            expected = float(before_value) - lr * float(grad)
            if not _close(float(actual), expected, tolerance):
                errors.append(f"第 {step} 步 参数 {name} 更新不满足 after = before - lr * gradient")
    return errors


def _as_feature_rows(value: Any) -> list[list[float]] | None:
    if not isinstance(value, list) or not value:
        return None
    if all(isinstance(item, (int, float)) for item in value):
        return [[float(item)] for item in value]
    rows: list[list[float]] = []
    for row in value:
        if not isinstance(row, list) or not row or not all(isinstance(item, (int, float)) for item in row):
            return None
        rows.append([float(item) for item in row])
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        return None
    return rows


def _is_numeric_vector(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, (int, float)) for item in value)


def _numeric_list(value: Any) -> list[float] | None:
    if not _is_numeric_vector(value):
        return None
    return [float(item) for item in value]


def _ml_parameters(state: dict[str, Any]) -> dict[str, Any] | None:
    params = state.get("parameters") or state.get("params")
    if isinstance(params, dict):
        return params
    weights = state.get("weights") or state.get("w")
    if weights is None:
        return None
    params = {"w": weights}
    if "b" in state:
        params["b"] = state["b"]
    return params


def _ml_gradient(state: dict[str, Any]) -> Any:
    return state.get("gradient") or state.get("gradients") or state.get("grad")


def _parameter_weights(params: dict[str, Any]) -> list[float] | None:
    for key in ("w", "weights", "theta"):
        value = params.get(key)
        if isinstance(value, (int, float)):
            return [float(value)]
        if _is_numeric_vector(value):
            return [float(item) for item in value]
    numeric_named = [(name, value) for name, value in params.items() if str(name).startswith("w") and isinstance(value, (int, float))]
    if numeric_named:
        return [float(value) for _name, value in sorted(numeric_named)]
    return None


def _parameter_bias(params: dict[str, Any]) -> float:
    value = params.get("b", params.get("bias", 0.0))
    return float(value) if isinstance(value, (int, float)) else 0.0


def _linear_gradient_weights(rows: list[list[float]], labels: list[float], predictions: list[float]) -> list[float]:
    n = len(labels)
    width = len(rows[0])
    return [
        sum((predictions[i] - labels[i]) * rows[i][j] for i in range(n)) / n
        for j in range(width)
    ]


def _linear_gradient_bias(labels: list[float], predictions: list[float]) -> float:
    return sum(pred - label for pred, label in zip(predictions, labels)) / len(labels)


def _gradient_weights(gradient: Any, expected_len: int) -> list[float] | None:
    if isinstance(gradient, (int, float)) and expected_len == 1:
        return [float(gradient)]
    if _is_numeric_vector(gradient) and len(gradient) == expected_len:
        return [float(item) for item in gradient]
    if not isinstance(gradient, dict):
        return None
    for key in ("w", "weights", "theta"):
        value = gradient.get(key)
        if isinstance(value, (int, float)) and expected_len == 1:
            return [float(value)]
        if _is_numeric_vector(value) and len(value) == expected_len:
            return [float(item) for item in value]
    named = [(name, value) for name, value in gradient.items() if str(name).startswith("w") and isinstance(value, (int, float))]
    if len(named) == expected_len:
        return [float(value) for _name, value in sorted(named)]
    return None


def _gradient_bias(gradient: Any) -> float | None:
    if not isinstance(gradient, dict):
        return None
    value = gradient.get("b", gradient.get("bias"))
    return float(value) if isinstance(value, (int, float)) else None


def _gradient_value_for_name(gradient: Any, name: str) -> Any:
    if isinstance(gradient, dict):
        if name in gradient:
            return gradient[name]
        if name == "b":
            return gradient.get("bias")
    return None


def _validate_heap_property(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        heap = (event.state or {}).get("heap")
        if not isinstance(heap, list) or not heap or not all(isinstance(x, (int, float)) for x in heap):
            continue
        mode = (event.state or {}).get("heap_type") or "min"
        for i, value in enumerate(heap):
            left, right = 2 * i + 1, 2 * i + 2
            for child in (left, right):
                if child >= len(heap):
                    continue
                if mode == "max" and value < heap[child]:
                    errors.append(f"第 {event.step} 步 heap[{i}] 小于子节点，不满足大顶堆")
                if mode != "max" and value > heap[child]:
                    errors.append(f"第 {event.step} 步 heap[{i}] 大于子节点，不满足小顶堆")
    return errors


def _validate_recursion_frame_balance(trace: SemanticTrace) -> list[str]:
    if not _trace_has_recursion_signal(trace):
        return []
    errors: list[str] = []
    stack: list[str] = []
    open_frames: set[str] = set()
    for event in trace.events:
        for frame in sorted(_frame_targets(event)):
            if event.op == SemanticOp.ENTER:
                stack.append(frame)
                open_frames.add(frame)
            elif event.op == SemanticOp.EXIT:
                if frame not in open_frames:
                    errors.append(f"第 {event.step} 步递归 frame {frame} 未进入就退出")
                    continue
                if stack and stack[-1] != frame:
                    errors.append(f"第 {event.step} 步递归 frame {frame} 跳帧退出，当前应退出 {stack[-1]}")
                    stack = [item for item in stack if item != frame]
                else:
                    stack.pop()
                open_frames.discard(frame)
    for frame in stack:
        errors.append(f"递归 frame {frame} 缺少 exit")
    return errors


def _trace_has_recursion_signal(trace: SemanticTrace) -> bool:
    algorithm = (trace.algorithm or "").lower()
    if any(token in algorithm for token in ("tree", "dfs", "recursion", "backtracking", "permutation", "树", "递归", "回溯", "全排列")):
        return True
    for event in trace.events:
        state = event.state or {}
        if any(key in state for key in ("call_stack", "recursion_tree", "search_tree", "return_values")):
            return True
        if _frame_targets(event):
            return True
    return False


def _frame_targets(event) -> set[str]:
    return {ref for ref in _event_target_ids(event) if ref.startswith("frame:")}


def _validate_trie_prefix_count(trace: SemanticTrace) -> list[str]:
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    words = input_data.get("words")
    prefix = input_data.get("prefix")
    if not isinstance(words, list) or not all(isinstance(word, str) for word in words) or not isinstance(prefix, str):
        return []
    if not _trace_has_trie_signal(trace):
        return []
    errors: list[str] = []
    expected_answer = sum(1 for word in words if word.startswith(prefix))
    saw_count = False
    for event in trace.events:
        state = event.state or {}
        trie = state.get("trie")
        if not isinstance(trie, dict):
            continue
        state_count = state.get("prefix_count")
        if isinstance(state_count, int) and (event.op == SemanticOp.MARK or event.role == "answer" or state.get("answer") is not None):
            saw_count = True
            partial = prefix if event.role == "answer" or state.get("answer") is not None else _trie_partial_prefix_for_state(prefix, state)
            expected = sum(1 for word in words if word.startswith(partial))
            if state_count != expected:
                errors.append(f"第 {event.step} 步 Trie prefix_count 应为 {expected}，实际为 {state_count}")
        answer = state.get("answer", event.value)
        if (event.role == "answer" or state.get("answer") is not None) and isinstance(answer, int) and answer != expected_answer:
            errors.append(f"第 {event.step} 步 Trie prefix_count 答案应为 {expected_answer}，实际为 {answer}")
        if event.role == "answer" or state.get("answer") is not None:
            node_counts = _trie_node_counts_for_prefixes(words)
            for node in trie.get("nodes") or []:
                if not isinstance(node, dict):
                    continue
                label = _trie_node_path_label(str(node.get("id", "")), trie)
                if label is None:
                    continue
                expected = node_counts.get(label, 0)
                actual = _trie_node_count(node)
                if actual is not None:
                    saw_count = True
                    if actual != expected:
                        errors.append(f"第 {event.step} 步 Trie prefix_count[{node.get('id')}] 应为 {expected}，实际为 {actual}")
    if not saw_count:
        errors.append("Trie prefix_count 缺少 count / prefix_count 证据")
    return errors


def _trace_has_trie_signal(trace: SemanticTrace) -> bool:
    algorithm = (trace.algorithm or "").lower()
    if "trie" in algorithm or "前缀树" in algorithm:
        return True
    for event in trace.events:
        state = event.state or {}
        contract = state.get("family_contract")
        if isinstance(contract, dict) and str(contract.get("family", "")).lower() == "trie":
            return True
        if isinstance(state.get("trie"), dict):
            return True
    return False


def _trie_node_counts_for_prefixes(words: list[str]) -> dict[str, int]:
    counts = {"": len(words)}
    for word in words:
        for index in range(1, len(word) + 1):
            prefix = word[:index]
            counts[prefix] = counts.get(prefix, 0) + 1
    return counts


def _trie_node_count(node: dict[str, Any]) -> int | None:
    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    for key in ("prefix_count", "count", "pass_count"):
        value = node.get(key, meta.get(key))
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _trie_node_path_label(node_id: str, trie: dict[str, Any]) -> str | None:
    nodes = trie.get("nodes")
    edges = trie.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return None
    labels = {
        str(node.get("id")): str(node.get("label", ""))
        for node in nodes
        if isinstance(node, dict) and node.get("id") is not None
    }
    if node_id not in labels:
        return None
    if node_id == "root":
        return ""
    parents: dict[str, str] = {}
    for edge in edges:
        if isinstance(edge, (list, tuple)) and len(edge) >= 2:
            parents[str(edge[1])] = str(edge[0])
    pieces: list[str] = []
    current = node_id
    seen: set[str] = set()
    while current != "root":
        if current in seen or current not in labels:
            return None
        seen.add(current)
        pieces.append(labels[current])
        if current not in parents:
            return None
        current = parents[current]
    return "".join(reversed(pieces))


def _trie_partial_prefix_for_state(prefix: str, state: dict[str, Any]) -> str:
    index = state.get("i")
    if isinstance(index, int) and index >= 0:
        return prefix[: index + 1]
    current = state.get("current")
    if isinstance(current, str) and current not in {"root", "missing"}:
        return prefix
    return prefix


def _validate_monotonic_stack(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        stack = state.get("stack")
        mode = state.get("stack_order") or state.get("monotonic")
        if mode not in {"increasing", "decreasing"} or not isinstance(stack, list):
            continue
        values = _stack_values(state, stack)
        if values is None:
            continue
        pairs = zip(values, values[1:])
        if mode == "increasing" and any(a > b for a, b in pairs):
            errors.append(f"第 {event.step} 步 stack 不满足单调递增")
        if mode == "decreasing" and any(a < b for a, b in pairs):
            errors.append(f"第 {event.step} 步 stack 不满足单调递减")
        errors.extend(_validate_monotonic_stack_answer_write(event))
    return errors


def _validate_monotonic_stack_key_step_coverage(trace: SemanticTrace) -> list[str]:
    sequence = _monotonic_stack_input_sequence(trace)
    if sequence is None or len(sequence) > SMALL_MONOTONIC_STACK_INPUT_LIMIT:
        return []
    if not _trace_has_monotonic_stack_signal(trace):
        return []
    missing: list[str] = []
    if not _trace_has_stack_push(trace):
        missing.append("push")
    requires_pop, requires_answer_write = _monotonic_stack_requires_pop_and_answer(sequence)
    if requires_pop and not _trace_has_stack_pop(trace):
        missing.append("pop")
    if requires_answer_write and not _trace_has_answer_write(trace):
        missing.append("answer_write")
    if missing:
        return [f"failure_type=coverage_error: 单调栈缺少关键步骤覆盖：{', '.join(missing)}"]
    return []


def _monotonic_stack_input_sequence(trace: SemanticTrace) -> list[Any] | None:
    if not isinstance(trace.input_data, dict):
        return None
    for key in ("temperatures", "nums", "heights"):
        value = trace.input_data.get(key)
        if isinstance(value, list):
            return value
    return None


def _trace_has_monotonic_stack_signal(trace: SemanticTrace) -> bool:
    algorithm = (trace.algorithm or "").lower()
    if "单调栈" in trace.algorithm or "monotonic stack" in algorithm:
        return True
    for event in trace.events:
        state = event.state or {}
        if state.get("stack_order") in {"increasing", "decreasing"} or state.get("monotonic") in {"increasing", "decreasing"}:
            return True
    return False


def _monotonic_stack_requires_pop_and_answer(sequence: list[Any]) -> tuple[bool, bool]:
    stack: list[int] = []
    requires = False
    for i, value in enumerate(sequence):
        while stack and isinstance(sequence[stack[-1]], (int, float)) and isinstance(value, (int, float)) and sequence[stack[-1]] < value:
            requires = True
            stack.pop()
        stack.append(i)
    return requires, requires


def _trace_has_stack_push(trace: SemanticTrace) -> bool:
    return any(event.op == SemanticOp.PUSH and "stack" in _event_target_ids(event) for event in trace.events)


def _trace_has_stack_pop(trace: SemanticTrace) -> bool:
    return any(event.op == SemanticOp.POP and "stack" in _event_target_ids(event) for event in trace.events)


def _trace_has_answer_write(trace: SemanticTrace) -> bool:
    for event in trace.events:
        if event.op != SemanticOp.SET:
            continue
        for ref in _event_target_ids(event):
            parsed = parse_target(ref)
            if parsed.kind == "indexed" and parsed.name in {"answer", "answers", "ans"}:
                return True
    return False


def _stack_values(state: dict[str, Any], stack: list[Any]) -> list[Any] | None:
    values = state.get("stack_values")
    if isinstance(values, list) and len(values) == len(stack) and all(isinstance(x, (int, float)) for x in values):
        return values
    nums = state.get("nums") or state.get("temperatures") or state.get("heights")
    if isinstance(nums, list) and all(isinstance(i, int) and 0 <= i < len(nums) for i in stack):
        vals = [nums[i] for i in stack]
        if all(isinstance(x, (int, float)) for x in vals):
            return vals
    if all(isinstance(x, (int, float)) for x in stack):
        return stack
    return None


def _validate_monotonic_stack_answer_write(event) -> list[str]:
    if event.op != SemanticOp.SET:
        return []
    state = event.state or {}
    temperatures = state.get("temperatures") or state.get("nums") or state.get("heights")
    answer = state.get("answer") or state.get("answers") or state.get("ans")
    i = state.get("i")
    if not isinstance(temperatures, list) or not isinstance(answer, list) or not isinstance(i, int):
        return []
    errors: list[str] = []
    for target in event.targets:
        parsed = parse_target(target.id)
        if parsed.kind != "indexed" or parsed.name not in {"answer", "answers", "ans"} or len(parsed.indices) != 1:
            continue
        j = parsed.indices[0]
        if not (0 <= j < len(answer) and 0 <= i < len(temperatures)):
            continue
        current = temperatures[i]
        previous = temperatures[j]
        actual = answer[j]
        expected = i - j
        if isinstance(current, (int, float)) and isinstance(previous, (int, float)) and current <= previous:
            errors.append(f"第 {event.step} 步 answer[{j}] 写入时当前值未打破单调栈条件")
        if actual != expected:
            errors.append(f"第 {event.step} 步 answer[{j}] 应为 {expected}，实际为 {actual}")
        expected_deps = {f"{_sequence_name_for_answer_state(state)}[{j}]", f"{_sequence_name_for_answer_state(state)}[{i}]"}
        actual_deps = _event_ref_ids(event.deps)
        if event.deps and not expected_deps <= actual_deps:
            errors.append(f"第 {event.step} 步 answer[{j}] 依赖应包含 {', '.join(sorted(expected_deps))}")
    return errors


def _sequence_name_for_answer_state(state: dict[str, Any]) -> str:
    if isinstance(state.get("temperatures"), list):
        return "temperatures"
    if isinstance(state.get("heights"), list):
        return "heights"
    return "nums"


def _validate_bst_order(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        tree = (event.state or {}).get("tree") or (event.state or {}).get("binary_tree")
        if not _tree_has_layout(tree, "bst"):
            continue
        nodes, edges = _tree_nodes_edges(tree)
        children = _children_map(edges)
        roots = _roots(nodes, edges)
        for root in roots:
            errors.extend(_check_bst_node(root, children, nodes, None, None, event.step))
    return errors


def _tree_has_layout(tree: Any, layout: str) -> bool:
    if not isinstance(tree, dict):
        return False
    meta = tree.get("meta") if isinstance(tree.get("meta"), dict) else {}
    return tree.get("kind") == layout or tree.get("type") == layout or meta.get("kind") == layout


def _tree_nodes_edges(tree: dict[str, Any]) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    nodes: dict[str, Any] = {}
    for node in tree.get("nodes") or []:
        if isinstance(node, dict):
            node_id = str(node.get("id"))
            value = node.get("value", node.get("label", node_id))
        else:
            node_id = str(node)
            value = node
        nodes[node_id] = _as_number(value)
    edges = []
    for edge in tree.get("edges") or []:
        if isinstance(edge, dict):
            src = edge.get("from", edge.get("source"))
            dst = edge.get("to", edge.get("target"))
        elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
            src, dst = edge[0], edge[1]
        else:
            continue
        if src is None or dst is None:
            continue
        edges.append((str(src), str(dst)))
    return nodes, edges


def _children_map(edges: list[tuple[str, str]]) -> dict[str, list[str]]:
    children: dict[str, list[str]] = {}
    for src, dst in edges:
        children.setdefault(src, []).append(dst)
    return children


def _roots(nodes: dict[str, Any], edges: list[tuple[str, str]]) -> list[str]:
    targets = {dst for _src, dst in edges}
    roots = [node for node in nodes if node not in targets]
    return roots or list(nodes)[:1]


def _check_bst_node(node: str, children: dict[str, list[str]], values: dict[str, Any], lo: Any, hi: Any, step: int) -> list[str]:
    errors: list[str] = []
    value = values.get(node)
    if isinstance(value, (int, float)):
        if lo is not None and value <= lo:
            errors.append(f"第 {step} 步 BST 节点 {node} 不大于下界")
        if hi is not None and value >= hi:
            errors.append(f"第 {step} 步 BST 节点 {node} 不小于上界")
    kids = children.get(node, [])
    if len(kids) >= 1:
        errors.extend(_check_bst_node(kids[0], children, values, lo, value if isinstance(value, (int, float)) else hi, step))
    if len(kids) >= 2:
        errors.extend(_check_bst_node(kids[1], children, values, value if isinstance(value, (int, float)) else lo, hi, step))
    return errors


def _validate_lca_node(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    p = str(input_data.get("p")) if "p" in input_data else None
    q = str(input_data.get("q")) if "q" in input_data else None
    if p is None or q is None:
        return errors
    for event in trace.events:
        state = event.state or {}
        tree = state.get("tree") or input_data.get("tree")
        lca = state.get("lca") or state.get("answer")
        if not isinstance(tree, dict) or lca is None:
            continue
        nodes, edges = _tree_nodes_edges(tree)
        children = _children_map(edges)
        roots = _roots(nodes, edges)
        expected = _lca(str(roots[0]), p, q, children) if roots else None
        if expected is not None and str(lca) != str(expected):
            errors.append(f"第 {event.step} 步 LCA 应为 {expected}，实际为 {lca}")
    return errors


def _lca(root: str, p: str, q: str, children: dict[str, list[str]]) -> str | None:
    if root == p or root == q:
        return root
    hits = []
    for child in children.get(root, []):
        got = _lca(child, p, q, children)
        if got is not None:
            hits.append(got)
    if len(hits) >= 2:
        return root
    return hits[0] if hits else None


def _validate_tree_diameter(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    algorithm = trace.algorithm or ""
    has_signal = "树直径" in algorithm or "diameter" in algorithm.lower() or any(
        "diameter" in (event.state or {}) for event in trace.events
    )
    if not has_signal:
        return errors
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    for event in trace.events:
        state = event.state or {}
        tree = state.get("tree") or input_data.get("tree")
        if not isinstance(tree, dict):
            continue
        current = state.get("current")
        height = state.get("height")
        diameter = state.get("diameter")
        if current is None or not isinstance(height, dict) or not isinstance(diameter, dict):
            continue
        node = str(current)
        nodes, edges = _tree_nodes_edges(tree)
        children = _children_map(edges)
        expected_height = _tree_height(node, children)
        child_diameters = [_dict_int(diameter, child, default=0) for child in children.get(node, [])]
        child_heights = [_tree_height(child, children) for child in children.get(node, [])]
        through = sum(sorted(child_heights, reverse=True)[:2])
        expected_diameter = max([through, *child_diameters], default=0)
        actual_height = _dict_int(height, node)
        actual_diameter = _dict_int(diameter, node)
        if node in nodes and actual_height is not None and actual_height != expected_height:
            errors.append(f"第 {event.step} 步树直径 height[{node}] 应为 {expected_height}")
        if node in nodes and actual_diameter is not None and actual_diameter != expected_diameter:
            errors.append(f"第 {event.step} 步树直径 diameter[{node}] 应为 {expected_diameter}")
    return errors


def _validate_tree_max_independent_set(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    algorithm = trace.algorithm or ""
    has_signal = "树形 dp" in algorithm.lower() or "树形 DP" in algorithm or any(
        "dp_take" in (event.state or {}) or "dp_skip" in (event.state or {}) for event in trace.events
    )
    if not has_signal:
        return errors
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    for event in trace.events:
        state = event.state or {}
        tree = state.get("tree") or input_data.get("tree")
        dp_take = state.get("dp_take")
        dp_skip = state.get("dp_skip")
        current = state.get("current")
        if not isinstance(tree, dict) or not isinstance(dp_take, dict) or not isinstance(dp_skip, dict) or current is None:
            continue
        node = str(current)
        nodes, edges = _tree_nodes_edges(tree)
        children = _children_map(edges)
        if node not in nodes:
            continue
        expected_take = _node_weight(tree, node) + sum(_dict_int(dp_skip, child, default=0) for child in children.get(node, []))
        expected_skip = sum(
            max(_dict_int(dp_take, child, default=0), _dict_int(dp_skip, child, default=0)) for child in children.get(node, [])
        )
        actual_take = _dict_int(dp_take, node)
        actual_skip = _dict_int(dp_skip, node)
        if actual_take is not None and actual_take != expected_take:
            errors.append(f"第 {event.step} 步树形 DP dp_take[{node}] 应为 {expected_take}")
        if actual_skip is not None and actual_skip != expected_skip:
            errors.append(f"第 {event.step} 步树形 DP dp_skip[{node}] 应为 {expected_skip}")
    return errors


def _validate_segment_tree_sums(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        nums = state.get("nums")
        tree = state.get("segment_tree")
        if not _is_numeric_sequence(nums) or not isinstance(tree, dict):
            continue
        for node in tree.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            left = _int_or_none(meta.get("l", meta.get("left")))
            right = _int_or_none(meta.get("r", meta.get("right")))
            actual = _int_or_none(meta.get("sum", meta.get("value", node.get("value"))))
            if left is None or right is None or actual is None:
                continue
            if not (0 <= left <= right < len(nums)):
                errors.append(f"第 {event.step} 步线段树节点 {node.get('id')} 覆盖区间越界")
                continue
            expected = sum(nums[left : right + 1])
            if actual != expected:
                errors.append(f"第 {event.step} 步线段树节点 {node.get('id')} 区间和应为 {expected}")
    return errors


def _validate_fenwick_tree(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        nums = state.get("nums")
        bit = state.get("bit") or state.get("fenwick")
        if not _is_numeric_sequence(nums) or not _is_numeric_sequence(bit):
            continue
        if len(bit) != len(nums) + 1:
            errors.append(f"第 {event.step} 步树状数组 bit 长度应为 nums 长度 + 1")
            continue
        expected = _fenwick_expected(nums)
        target_indices = _fenwick_target_indices(event)
        if target_indices:
            indices = sorted(index for index in target_indices if 1 <= index < len(expected))
        elif event.role == "answer":
            indices = list(range(1, len(expected)))
        elif event.op == SemanticOp.CREATE and any(bit[1:]):
            indices = list(range(1, len(expected)))
        else:
            continue
        for i in indices:
            if bit[i] != expected[i]:
                errors.append(f"第 {event.step} 步树状数组 bit[{i}] 应为 {expected[i]}")
    return errors


def _fenwick_target_indices(event) -> set[int]:
    indices: set[int] = set()
    for target_id in _event_target_ids(event):
        parsed = parse_target(target_id)
        if parsed.kind == "indexed" and parsed.name in {"bit", "fenwick"} and len(parsed.indices) == 1:
            index = parsed.indices[0]
            if isinstance(index, int):
                indices.add(index)
    return indices


def _validate_sparse_table(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    for event in trace.events:
        state = event.state or {}
        nums = state.get("nums") or input_data.get("nums")
        st = state.get("st") or state.get("sparse_table")
        if not _is_numeric_sequence(nums) or not _is_matrix(st):
            continue
        for k, row in enumerate(st):
            if not isinstance(row, list):
                continue
            span = 1 << k
            if span > len(nums):
                continue
            for i, value in enumerate(row):
                if value is None:
                    continue
                if not isinstance(value, (int, float)):
                    continue
                if i + span > len(nums):
                    continue
                expected = min(nums[i : i + span])
                if value != expected:
                    errors.append(f"第 {event.step} 步稀疏表 st[{k}][{i}] 应为 {expected}")
    return errors


def _validate_gcd_remainders(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    a = _int_or_none(input_data.get("a"))
    b = _int_or_none(input_data.get("b"))
    if a is None or b is None:
        return errors
    expected = _gcd_remainders(abs(a), abs(b))
    for event in trace.events:
        remainders = (event.state or {}).get("remainders")
        if not isinstance(remainders, list):
            continue
        for i, value in enumerate(remainders):
            if i >= len(expected) or not isinstance(value, int):
                continue
            if value != expected[i]:
                errors.append(f"第 {event.step} 步最大公约数 remainders[{i}] 应为 {expected[i]}")
    return errors


def _validate_fast_power_table(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    base = _int_or_none(input_data.get("base"))
    exponent = _int_or_none(input_data.get("exponent"))
    mod = _int_or_none(input_data.get("mod"))
    if base is None or exponent is None or mod is None or exponent < 0 or mod <= 0:
        return errors
    expected_bits = _bits_lsb_first(exponent)
    expected_powers = _fast_power_powers(base, exponent, mod)
    for event in trace.events:
        state = event.state or {}
        bits = state.get("bits")
        powers = state.get("powers")
        if isinstance(bits, list):
            for i, value in enumerate(bits):
                if i < len(expected_bits) and isinstance(value, int) and value != expected_bits[i]:
                    errors.append(f"第 {event.step} 步快速幂 bits[{i}] 应为 {expected_bits[i]}")
        if isinstance(powers, list):
            for i, value in enumerate(powers):
                if i < len(expected_powers) and isinstance(value, int) and value != expected_powers[i]:
                    errors.append(f"第 {event.step} 步快速幂 powers[{i}] 应为 {expected_powers[i]}")
    return errors


def _validate_sieve_primes(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    n = _int_or_none(input_data.get("n"))
    if n is None or n < 0:
        return errors
    expected = _sieve_flags(n)
    for event in trace.events:
        flags = (event.state or {}).get("is_prime")
        if not isinstance(flags, list) or len(flags) != len(expected):
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind != "indexed" or parsed.name != "is_prime" or len(parsed.indices) != 1:
                continue
            i = parsed.indices[0]
            if 0 <= i < len(expected) and isinstance(flags[i], bool) and flags[i] != expected[i]:
                errors.append(f"第 {event.step} 步筛法 is_prime[{i}] 应为 {expected[i]}")
    return errors


def _validate_pascal_combinations(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    n = _int_or_none(input_data.get("n"))
    k = _int_or_none(input_data.get("k"))
    if n is None or k is None or n < 0 or k < 0:
        return errors
    for event in trace.events:
        table = (event.state or {}).get("table")
        if not _is_matrix(table):
            continue
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind != "indexed" or parsed.name != "table" or len(parsed.indices) != 2:
                continue
            i, j = parsed.indices
            if not (0 <= i <= n and 0 <= j <= min(i, k) and i < len(table) and j < len(table[i])):
                continue
            value = table[i][j]
            if not isinstance(value, int):
                continue
            expected = _comb(i, j)
            if value != expected:
                errors.append(f"第 {event.step} 步组合数 table[{i}][{j}] 应为 {expected}")
    return errors


def _validate_bitmask_subset(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    nums = input_data.get("nums")
    if not isinstance(nums, list):
        return errors
    for event in trace.events:
        state = event.state or {}
        mask = _int_or_none(state.get("mask"))
        bits = state.get("bits")
        subset = state.get("subset")
        if mask is None or not isinstance(bits, list):
            continue
        expected_bits = [((mask >> i) & 1) for i in range(len(nums))]
        for target in event.targets:
            parsed = parse_target(target.id)
            if parsed.kind != "indexed" or parsed.name != "bits" or len(parsed.indices) != 1:
                continue
            i = parsed.indices[0]
            if i < len(expected_bits) and i < len(bits) and isinstance(bits[i], int) and bits[i] != expected_bits[i]:
                errors.append(f"第 {event.step} 步位掩码 bits[{i}] 应为 {expected_bits[i]}")
        expected_subset = [nums[i] for i, bit in enumerate(expected_bits) if bit]
        if event.role == "answer" and isinstance(subset, list) and subset != expected_subset:
            errors.append(f"第 {event.step} 步位掩码 subset 应为 {expected_subset}")
    return errors


def _validate_lowbit_decomposition(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    input_data = trace.input_data if isinstance(trace.input_data, dict) else {}
    n = _int_or_none(input_data.get("n"))
    if n is None or n < 0:
        return errors
    expected = _lowbit_parts(n)
    for event in trace.events:
        state = event.state or {}
        lowbit = _int_or_none(state.get("lowbit"))
        remaining = _int_or_none(state.get("remaining"))
        if lowbit is not None and remaining is not None and remaining > 0:
            expected_low = remaining & -remaining
            if lowbit != expected_low:
                errors.append(f"第 {event.step} 步 lowbit 应为 {expected_low}")
        lowbits = state.get("lowbits")
        if isinstance(lowbits, list):
            for i, value in enumerate(lowbits):
                if i < len(expected) and isinstance(value, int) and value != expected[i]:
                    errors.append(f"第 {event.step} 步 lowbit lowbits[{i}] 应为 {expected[i]}")
    return errors


def _fenwick_expected(nums: list[int | float]) -> list[int | float]:
    bit: list[int | float] = [0] * (len(nums) + 1)
    for i, value in enumerate(nums):
        j = i + 1
        while j <= len(nums):
            bit[j] += value
            j += j & -j
    return bit


def _gcd_remainders(a: int, b: int) -> list[int]:
    values: list[int] = []
    while b:
        r = a % b
        values.append(r)
        a, b = b, r
    return values


def _bits_lsb_first(value: int) -> list[int]:
    if value == 0:
        return [0]
    bits: list[int] = []
    while value:
        bits.append(value & 1)
        value >>= 1
    return bits


def _fast_power_powers(base: int, exponent: int, mod: int) -> list[int]:
    count = len(_bits_lsb_first(exponent))
    powers: list[int] = []
    cur = base % mod
    for _ in range(count):
        powers.append(cur)
        cur = (cur * cur) % mod
    return powers


def _sieve_flags(n: int) -> list[bool]:
    if n < 0:
        return []
    flags = [True] * (n + 1)
    if n >= 0:
        flags[0] = False
    if n >= 1:
        flags[1] = False
    p = 2
    while p * p <= n:
        if flags[p]:
            m = p * p
            while m <= n:
                flags[m] = False
                m += p
        p += 1
    return flags


def _comb(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    result = 1
    for i in range(1, k + 1):
        result = result * (n - k + i) // i
    return result


def _lowbit_parts(value: int) -> list[int]:
    parts: list[int] = []
    while value:
        low = value & -value
        parts.append(low)
        value -= low
    return parts


def _tree_height(node: str, children: dict[str, list[str]]) -> int:
    kids = children.get(node, [])
    if not kids:
        return 1
    return 1 + max(_tree_height(child, children) for child in kids)


def _node_weight(tree: dict[str, Any], node_id: str) -> int:
    for node in tree.get("nodes") or []:
        if not isinstance(node, dict) or str(node.get("id")) != node_id:
            continue
        value = node.get("weight", node.get("value", node.get("label", 1)))
        if isinstance(value, bool):
            return 1
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.lstrip("-").isdigit():
            return int(value)
        return 1
    return 1


def _validate_tarjan_lowlink(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        dfn = state.get("dfn") or state.get("disc")
        low = state.get("low") or state.get("lowlink")
        if not isinstance(dfn, dict) or not isinstance(low, dict):
            continue
        for node, value in low.items():
            if _dict_lookup(dfn, node) is not None and isinstance(value, int) and isinstance(_dict_lookup(dfn, node), int) and value > _dict_lookup(dfn, node):
                errors.append(f"第 {event.step} 步 low[{node}] 大于 dfn[{node}]")
        stack = state.get("stack")
        on_stack = state.get("on_stack")
        if isinstance(stack, list) and isinstance(on_stack, dict):
            stack_nodes = {str(node) for node in stack}
            for node, flagged in on_stack.items():
                if flagged is True and str(node) not in stack_nodes:
                    errors.append(f"第 {event.step} 步 Tarjan on_stack[{node}] 为 True 但节点不在 stack 中")
        component = state.get("component")
        if isinstance(component, list) and isinstance(stack, list):
            stack_nodes = {str(node) for node in stack}
            overlap = [node for node in component if str(node) in stack_nodes]
            if overlap:
                errors.append(f"第 {event.step} 步 Tarjan component 节点仍在 stack 中：{overlap[0]}")
    return errors


def _validate_articulation_bridges(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        dfn = state.get("dfn") or state.get("disc")
        low = state.get("low") or state.get("lowlink")
        parent = state.get("parent")
        if not isinstance(dfn, dict) or not isinstance(low, dict) or not isinstance(parent, dict):
            continue
        bridges = state.get("bridges")
        if isinstance(bridges, list):
            for edge in bridges:
                u, v = _edge_uv(edge)
                if u is None or v is None:
                    continue
                parent_u = _dict_lookup(parent, u)
                parent_v = _dict_lookup(parent, v)
                if _same_node(parent_v, u):
                    ancestor, child = u, v
                elif _same_node(parent_u, v):
                    ancestor, child = v, u
                else:
                    errors.append(f"第 {event.step} 步 桥 {u}-{v} 不是 DFS 树边")
                    continue
                child_low = _dict_int(low, child)
                ancestor_dfn = _dict_int(dfn, ancestor)
                if child_low is not None and ancestor_dfn is not None and child_low <= ancestor_dfn:
                    errors.append(f"第 {event.step} 步 桥 {ancestor}-{child} 不满足 low[{child}] > dfn[{ancestor}]")
        articulation = state.get("articulation")
        if isinstance(articulation, list):
            children = _children_by_parent(parent)
            for node in articulation:
                node_dfn = _dict_int(dfn, node)
                if node_dfn is None:
                    continue
                kids = children.get(str(node), [])
                root = _dict_lookup(parent, node) in {None, ""}
                if root:
                    if len(kids) <= 1:
                        errors.append(f"第 {event.step} 步 割点 {node} 是根节点但 DFS 子节点不足两个")
                    continue
                if not any((_dict_int(low, child) is not None and _dict_int(low, child) >= node_dfn) for child in kids):
                    errors.append(f"第 {event.step} 步 割点 {node} 缺少满足 low[child] >= dfn[{node}] 的子节点")
    return errors


def _children_by_parent(parent: dict[Any, Any]) -> dict[str, list[Any]]:
    children: dict[str, list[Any]] = {}
    for node, raw_parent in parent.items():
        if raw_parent in {None, ""}:
            continue
        children.setdefault(str(raw_parent), []).append(node)
    return children


def _validate_bipartite_matching(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        match = state.get("match")
        if not isinstance(match, dict):
            continue
        graph = state.get("graph") if isinstance(state.get("graph"), dict) else {}
        left_nodes = {str(node) for node in state.get("left_nodes", []) if node is not None}
        right_nodes = {str(node) for node in state.get("right_nodes", []) if node is not None}
        if not left_nodes and not right_nodes:
            left_nodes, right_nodes = _infer_bipartite_sides(graph, match)
        right_owner: dict[str, Any] = {}
        for left in left_nodes:
            mate = _dict_lookup(match, left)
            if mate in {None, ""}:
                continue
            if str(mate) not in right_nodes:
                errors.append(f"第 {event.step} 步 匹配 match[{left}] 指向非右侧点 {mate}")
            if graph and not _graph_has_edge(graph, left, mate):
                errors.append(f"第 {event.step} 步 匹配边 {left}-{mate} 不存在于 graph")
            previous = right_owner.get(str(mate))
            if previous is not None and not _same_node(previous, left):
                errors.append(f"第 {event.step} 步 匹配冲突：右侧点 {mate} 同时匹配 {previous} 和 {left}")
            right_owner[str(mate)] = left
            reverse = _dict_lookup(match, mate)
            if reverse not in {None, ""} and not _same_node(reverse, left):
                errors.append(f"第 {event.step} 步 匹配不一致：match[{left}]={mate} 但 match[{mate}]={reverse}")
        for right in right_nodes:
            mate = _dict_lookup(match, right)
            if mate in {None, ""}:
                continue
            if str(mate) not in left_nodes:
                errors.append(f"第 {event.step} 步 匹配 match[{right}] 指向非左侧点 {mate}")
            reverse = _dict_lookup(match, mate)
            if reverse not in {None, ""} and not _same_node(reverse, right):
                errors.append(f"第 {event.step} 步 匹配不一致：match[{right}]={mate} 但 match[{mate}]={reverse}")
    return errors


def _infer_bipartite_sides(graph: dict[Any, Any], match: dict[Any, Any]) -> tuple[set[str], set[str]]:
    left_nodes = {str(node) for node in graph}
    right_nodes = {str(nei) for neighbors in graph.values() if isinstance(neighbors, list) for nei in neighbors}
    if not left_nodes:
        for node, mate in match.items():
            if str(node).startswith("L"):
                left_nodes.add(str(node))
            if str(node).startswith("R"):
                right_nodes.add(str(node))
            if str(mate).startswith("L"):
                left_nodes.add(str(mate))
            if str(mate).startswith("R"):
                right_nodes.add(str(mate))
    return left_nodes, right_nodes


def _graph_has_edge(graph: dict[Any, Any], left: Any, right: Any) -> bool:
    neighbors = _dict_lookup(graph, left)
    return isinstance(neighbors, list) and any(_same_node(nei, right) for nei in neighbors)


def _validate_flow_capacity(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        state = event.state or {}
        capacity = state.get("capacity") or state.get("cap")
        flow = state.get("flow")
        if not isinstance(capacity, dict) or not isinstance(flow, dict):
            continue
        graph = state.get("graph") if isinstance(state.get("graph"), dict) else {}
        source = _dict_lookup(trace.input_data, "source") if isinstance(trace.input_data, dict) else state.get("source")
        sink = _dict_lookup(trace.input_data, "sink") if isinstance(trace.input_data, dict) else state.get("sink")
        for edge, raw_value in flow.items():
            value = _as_int(raw_value)
            cap = _as_int(_dict_lookup(capacity, edge))
            if value is None:
                continue
            if value < 0:
                errors.append(f"第 {event.step} 步 flow[{edge}] 为负数")
            if cap is not None and value > cap:
                errors.append(f"第 {event.step} 步 flow[{edge}] 超过容量 {cap}")
            if cap is None and graph:
                u, v = _flow_edge_uv(edge)
                if u is not None and v is not None and not _graph_has_edge(graph, u, v):
                    errors.append(f"第 {event.step} 步 flow[{edge}] 不在容量图中")
        balance = _flow_balance(flow)
        for node, value in balance.items():
            if _same_node(node, source) or _same_node(node, sink):
                continue
            if value != 0:
                errors.append(f"第 {event.step} 步 flow 在中间节点 {node} 不守恒：净流 {value}")
        bottleneck = state.get("bottleneck")
        if isinstance(bottleneck, int) and bottleneck < 0:
            errors.append(f"第 {event.step} 步 Edmonds-Karp bottleneck 不能为负数")
    return errors


def _flow_balance(flow: dict[Any, Any]) -> dict[str, int]:
    balance: dict[str, int] = {}
    for edge, raw_value in flow.items():
        value = _as_int(raw_value)
        if value is None:
            continue
        u, v = _flow_edge_uv(edge)
        if u is None or v is None:
            continue
        balance[str(u)] = balance.get(str(u), 0) - value
        balance[str(v)] = balance.get(str(v), 0) + value
    return balance


def _validate_convex_hull(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        geometry = (event.state or {}).get("geometry")
        if not isinstance(geometry, dict):
            continue
        points = _point_map(geometry.get("points") or [])
        hull = geometry.get("hull")
        if not isinstance(hull, list) or len(hull) < 3:
            continue
        coords = [points.get(str(pid)) for pid in hull]
        if any(p is None for p in coords):
            errors.append(f"第 {event.step} 步 hull 引用了不存在的点")
            continue
        signs = []
        for i in range(len(coords)):
            a, b, c = coords[i], coords[(i + 1) % len(coords)], coords[(i + 2) % len(coords)]
            cross = _cross(a, b, c)
            if cross:
                signs.append(cross > 0)
        if signs and any(s != signs[0] for s in signs):
            errors.append(f"第 {event.step} 步 hull 不是一致转向的凸多边形")
    return errors


def _point_map(points: list[Any]) -> dict[str, tuple[float, float]]:
    result = {}
    for i, point in enumerate(points):
        if isinstance(point, dict):
            point_id = str(point.get("id", i))
            x, y = point.get("x"), point.get("y")
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            point_id = str(i)
            x, y = point[0], point[1]
        else:
            continue
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            result[point_id] = (float(x), float(y))
    return result


def _cross(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _validate_backtracking_tree(trace: SemanticTrace) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        tree = (event.state or {}).get("recursion_tree") or (event.state or {}).get("search_tree")
        if not isinstance(tree, dict):
            continue
        nodes, edges = _tree_nodes_edges(tree)
        roots = _roots(nodes, edges)
        if len(roots) != 1:
            errors.append(f"第 {event.step} 步回溯搜索树应只有一个根")
        children = _children_map(edges)
        seen = set()
        stack = roots[:]
        while stack:
            node = stack.pop()
            if node in seen:
                errors.append(f"第 {event.step} 步回溯搜索树存在重复访问节点：{node}")
                break
            seen.add(node)
            stack.extend(children.get(node, []))
        if len(edges) > max(0, len(nodes) - 1):
            errors.append(f"第 {event.step} 步回溯搜索树边数超过节点数约束")
    return errors

__all__ = [name for name in globals() if not name.startswith("__")]
