"""Replay frozen Stage1 solution/tracker code on every benchmark sample."""

from __future__ import annotations

import argparse
import json
import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.replay_llm_specs import replay_artifact_data


def build_jobs(benchmark: dict[str, Any], report: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = {str(row.get("case_id")): row for row in report.get("results") or [] if row.get("json")}
    jobs = []
    for case in benchmark.get("cases") or []:
        case_id = str(case.get("id") or case.get("case_id") or case.get("algorithm_id") or "")
        if case_id not in artifacts:
            raise ValueError(f"missing final artifact for {case_id}")
        for ordinal, sample in enumerate(case.get("samples") or []):
            sample_index = int(sample.get("index", ordinal))
            jobs.append(
                {
                    "case_id": case_id,
                    "family": case.get("family"),
                    "family_id": case.get("family_id"),
                    "subfamily_id": case.get("subfamily_id"),
                    "gate_layer": case.get("gate_layer"),
                    "sample_index": sample_index,
                    "sample_role": "primary_sample0" if sample_index == 0 else "additional_sample",
                    "input_data": sample.get("input_data"),
                    "expected": sample.get("expected"),
                    "artifact": artifacts[case_id].get("json"),
                }
            )
    jobs.sort(key=lambda row: (row["case_id"], row["sample_index"]))
    return jobs


def _summarize(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key))].append(row)
    return {
        name: {
            "total": len(items),
            "passed": sum(item.get("ok") is True for item in items),
            "pass_rate": sum(item.get("ok") is True for item in items) / len(items),
        }
        for name, items in sorted(grouped.items())
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()
    benchmark_path = args.benchmark if args.benchmark.is_absolute() else ROOT / args.benchmark
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl = output_dir / "cross_input_replay.jsonl"
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    source_report = json.loads(report_path.read_text(encoding="utf-8"))
    jobs = build_jobs(benchmark, source_report)
    done = set()
    rows = []
    if output_jsonl.exists():
        for line in output_jsonl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                row.setdefault(
                    "sample_role",
                    "primary_sample0" if int(row.get("sample_index", -1)) == 0 else "additional_sample",
                )
                rows.append(row)
                done.add((row["case_id"], int(row["sample_index"])))
    lock = threading.Lock()

    def run(job: dict[str, Any]) -> dict[str, Any]:
        artifact_path = Path(str(job["artifact"]))
        if not artifact_path.is_absolute():
            artifact_path = ROOT / artifact_path
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        replay = replay_artifact_data(
            artifact,
            artifact_path=artifact_path,
            case_id=job["case_id"],
            family_id=job.get("family_id"),
            subfamily_id=job.get("subfamily_id"),
            input_data=job.get("input_data"),
            expected=job.get("expected"),
        )
        return {**job, **replay, "sample_index": job["sample_index"]}

    pending = [job for job in jobs if (job["case_id"], job["sample_index"]) not in done]
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = {executor.submit(run, job): job for job in pending}
        for future in as_completed(futures):
            row = future.result()
            with lock:
                with output_jsonl.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)
            print(f"REPLAY {row['case_id']} sample={row['sample_index']} ok={row['ok']}", flush=True)
    rows.sort(key=lambda row: (row["case_id"], int(row["sample_index"])))
    unique = {(row["case_id"], int(row["sample_index"])) for row in rows}
    if len(rows) != len(jobs) or len(unique) != len(jobs):
        raise ValueError(f"incomplete replay rows={len(rows)} unique={len(unique)} expected={len(jobs)}")
    passed = sum(row.get("ok") is True for row in rows)
    report = {
        "kind": "cross_input_replay_report",
        "total": len(rows),
        "passed": passed,
        "failed": len(rows) - passed,
        "pass_rate": passed / len(rows) if rows else 0.0,
        "unique_cases": len({row["case_id"] for row in rows}),
        "by_sample_index": _summarize(rows, "sample_index"),
        "by_sample_role": _summarize(rows, "sample_role"),
        "by_family": _summarize(rows, "family_id"),
        "by_gate_layer": _summarize(rows, "gate_layer"),
        "results": rows,
    }
    (output_dir / "cross_input_replay_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"total": len(rows), "passed": passed, "failed": len(rows) - passed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
