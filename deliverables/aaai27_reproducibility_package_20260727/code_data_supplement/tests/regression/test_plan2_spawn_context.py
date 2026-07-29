from __future__ import annotations

import concurrent.futures
import queue
from types import SimpleNamespace

from algolab.runtime import sandbox
from benchmark.cases import BenchmarkInput
from scripts import run_llm_benchmark as benchmark_runner


def _reject_default_context(*_args, **_kwargs):
    raise AssertionError("multiprocessing constructors must come from the spawn context")


class _CompletedQueue:
    def __init__(self) -> None:
        self._items: list[dict] = []

    def put(self, item: dict) -> None:
        self._items.append(item)

    def get_nowait(self) -> dict:
        if not self._items:
            raise queue.Empty
        return self._items.pop(0)


class _CompletedProcess:
    def __init__(self, *, target, args) -> None:
        self.target = target
        self.args = args
        self._result_queue = args[-1]

    def start(self) -> None:
        self._result_queue.put(
            {
                "type": "result",
                "result": {"ok": True, "source": "completed-test-process"},
            }
        )

    def is_alive(self) -> bool:
        return False

    def join(self, _timeout: float | None = None) -> None:
        return None


class _CompletedSpawnContext:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.process: _CompletedProcess | None = None

    def Queue(self) -> _CompletedQueue:
        self.calls.append("Queue")
        return _CompletedQueue()

    def Process(self, *, target, args) -> _CompletedProcess:
        self.calls.append("Process")
        self.process = _CompletedProcess(target=target, args=args)
        return self.process


def test_benchmark_outer_process_uses_one_spawn_context(monkeypatch) -> None:
    spawn_context = _CompletedSpawnContext()
    requested_methods: list[str] = []

    def get_context(start_method: str) -> _CompletedSpawnContext:
        requested_methods.append(start_method)
        return spawn_context

    monkeypatch.setattr(benchmark_runner.mp, "get_context", get_context)
    monkeypatch.setattr(benchmark_runner.mp, "Queue", _reject_default_context)
    monkeypatch.setattr(benchmark_runner.mp, "Process", _reject_default_context)

    case = SimpleNamespace(
        id="spawn-context-case",
        title="Spawn context case",
        problem="No API benchmark process construction",
        family="test",
        strategy="test",
        family_id="test_family",
        subfamily_id="test_subfamily",
        gate_layer="test",
        support_level="test",
        process_profile="test",
    )
    sample = BenchmarkInput(input_data={"value": 1}, expected=2)
    args = SimpleNamespace(timeout_s=1, case_set="unseen", condition="algolab_full")

    result = benchmark_runner.run_one_with_timeout(case, sample, 0, args)

    assert result == {"ok": True, "source": "completed-test-process"}
    assert requested_methods == ["spawn"]
    assert spawn_context.calls == ["Queue", "Process"]
    assert spawn_context.process is not None
    assert spawn_context.process.target is benchmark_runner._run_one_worker


class _RecordingSpawnContext:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.calls: list[str] = []
        self.process_start_methods: list[str | None] = []

    def Queue(self, *args, **kwargs):
        self.calls.append("Queue")
        return self.delegate.Queue(*args, **kwargs)

    def Process(self, *args, **kwargs):
        self.calls.append("Process")
        process = self.delegate.Process(*args, **kwargs)
        self.process_start_methods.append(getattr(process, "_start_method", None))
        return process


def test_sandbox_process_uses_spawn_context_inside_thread(monkeypatch) -> None:
    real_get_context = sandbox.mp.get_context
    recording_context = _RecordingSpawnContext(real_get_context("spawn"))
    requested_methods: list[str] = []

    def get_context(start_method: str | None = None):
        if start_method == "spawn":
            requested_methods.append(start_method)
            return recording_context
        return real_get_context(start_method)

    monkeypatch.setattr(sandbox.mp, "get_context", get_context)
    monkeypatch.setattr(sandbox.mp, "Queue", _reject_default_context)
    monkeypatch.setattr(sandbox.mp, "Process", _reject_default_context)

    code = """
def solve(input_data):
    return {"answer": input_data["value"] + 1}
"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            sandbox.run_function,
            code,
            "solve",
            {"value": 41},
            10,
        )
        result = future.result(timeout=20)

    assert result == {"answer": 42}
    assert requested_methods == ["spawn"]
    assert recording_context.calls == ["Queue", "Process"]
    assert recording_context.process_start_methods == ["spawn"]
