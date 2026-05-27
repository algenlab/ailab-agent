"""Structured trace builder used by generated tracker code."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class Tracer:
    def __init__(
        self,
        input_data: Any,
        *,
        algorithm: str = "",
        pseudocode: list[str] | None = None,
        max_events: int = 80,
        policy: str = "auto",
    ) -> None:
        self.input_data = deepcopy(input_data)
        self.algorithm = algorithm or "算法轨迹"
        self.pseudocode = list(pseudocode or [])
        self.max_events = max_events
        self.policy = policy
        self._events: list[dict[str, Any]] = []
        self._result: Any = None
        self._expected_updates: dict[str, int] = {}
        self._recorded_updates: dict[str, int] = {}

    def create(self, target: str, **kwargs: Any) -> None:
        self._add("create", [target], **kwargs)

    def set(self, target: str, **kwargs: Any) -> None:
        self._record_update(target)
        self._add("set", [target], **kwargs)

    def mark(self, target: str, **kwargs: Any) -> None:
        self._record_update(target)
        self._add("mark", [target], **kwargs)

    def unmark(self, target: str, **kwargs: Any) -> None:
        self._record_update(target)
        self._add("unmark", [target], **kwargs)

    def move(self, target: str, **kwargs: Any) -> None:
        self._record_update(target)
        self._add("move", [target], **kwargs)

    def compare(self, targets: list[str], **kwargs: Any) -> None:
        self._add("compare", targets, **kwargs)

    def link(self, target: str, **kwargs: Any) -> None:
        self._record_update(target)
        self._add("link", [target], **kwargs)

    def unlink(self, target: str, **kwargs: Any) -> None:
        self._record_update(target)
        self._add("unlink", [target], **kwargs)

    def push(self, target: str, **kwargs: Any) -> None:
        self._record_update(target)
        self._add("push", [target], **kwargs)

    def pop(self, target: str, **kwargs: Any) -> None:
        self._record_update(target)
        self._add("pop", [target], **kwargs)

    def enter(self, target: str, **kwargs: Any) -> None:
        self._record_update(target)
        self._add("enter", [target], **kwargs)

    def exit(self, target: str, **kwargs: Any) -> None:
        self._record_update(target)
        self._add("exit", [target], **kwargs)

    def explain(self, target: str | None = None, **kwargs: Any) -> None:
        self._add("explain", [target] if target else [], **kwargs)

    def expect_updates(self, name: str, count: int) -> None:
        self._expected_updates[str(name)] = int(count)

    def result(self, value: Any) -> None:
        self._result = deepcopy(value)

    def to_trace(self) -> dict[str, Any]:
        self._validate_expected_updates()
        raw_events = self._events
        sampled = self._should_sample(raw_events)
        selected = self._sample_events(raw_events, self.max_events) if sampled else raw_events
        events = [self._with_step(index, event) for index, event in enumerate(selected)]
        self._attach_meta(events, sampled=sampled, raw_event_count=len(raw_events))
        return {
            "schema_version": "semantic-trace-v1",
            "algorithm": self.algorithm,
            "input_data": deepcopy(self.input_data),
            "result": deepcopy(self._result),
            "pseudocode": list(self.pseudocode),
            "events": events,
        }

    def _add(
        self,
        op: str,
        targets: list[str],
        *,
        state: dict[str, Any] | None = None,
        value: Any = None,
        deps: list[str] | None = None,
        role: str = "",
        reason: str = "",
        code_line: int = 1,
        before: Any = None,
        after: Any = None,
        teaching: dict[str, Any] | None = None,
        interaction: dict[str, Any] | None = None,
    ) -> None:
        self._events.append(
            {
                "step": len(self._events),
                "op": op,
                "targets": [{"id": item} for item in targets],
                "value": deepcopy(value),
                "before": deepcopy(before),
                "after": deepcopy(after),
                "deps": [{"id": item} for item in (deps or [])],
                "role": role or "",
                "reason": reason or "",
                "state": deepcopy(state or {}),
                "code_line": int(code_line or 1),
                "teaching": deepcopy(teaching),
                "interaction": deepcopy(interaction),
            }
        )

    def _record_update(self, target: str) -> None:
        name = target.split("[", 1)[0]
        self._recorded_updates[name] = self._recorded_updates.get(name, 0) + 1

    def _validate_expected_updates(self) -> None:
        if self.policy not in {"strict", "full", "auto"}:
            return
        for name, expected in self._expected_updates.items():
            recorded = self._recorded_updates.get(name, 0)
            if expected <= self.max_events and recorded < expected:
                raise ValueError(f"{name} expected {expected} updates, recorded {recorded}")

    def _should_sample(self, raw_events: list[dict[str, Any]]) -> bool:
        if self.policy == "full" or self.policy == "strict":
            return False
        if self.policy == "sampled":
            return len(raw_events) > self.max_events
        if self.policy != "auto":
            return False
        expected_total = sum(self._expected_updates.values())
        if expected_total:
            return expected_total > self.max_events
        return len(raw_events) > self.max_events

    def _attach_meta(self, events: list[dict[str, Any]], *, sampled: bool, raw_event_count: int) -> None:
        if not events:
            return
        coverage = {}
        for name, expected in self._expected_updates.items():
            recorded = self._recorded_updates.get(name, 0)
            coverage[name] = 1.0 if expected == 0 else round(recorded / expected, 6)
        meta = {
            "policy": self.policy,
            "max_events": self.max_events,
            "raw_event_count": raw_event_count,
            "emitted_event_count": len(events),
            "sampled": sampled,
            "expected_updates": dict(self._expected_updates),
            "recorded_updates": dict(self._recorded_updates),
            "coverage": coverage,
        }
        state = dict(events[-1].get("state") or {})
        state["_trace_meta"] = meta
        events[-1]["state"] = state

    def _sample_events(self, events: list[dict[str, Any]], max_events: int) -> list[dict[str, Any]]:
        if max_events <= 0 or len(events) <= max_events:
            return events
        if max_events == 1:
            return [events[-1]]
        selected_indices = {0, len(events) - 1}
        remaining = max_events - len(selected_indices)
        if remaining > 0:
            span = len(events) - 1
            for k in range(1, remaining + 1):
                selected_indices.add(round(k * span / (remaining + 1)))
        return [events[index] for index in sorted(selected_indices)][:max_events]

    def _with_step(self, index: int, event: dict[str, Any]) -> dict[str, Any]:
        item = deepcopy(event)
        item["step"] = index
        return item
