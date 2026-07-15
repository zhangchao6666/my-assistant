from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openai import APIConnectionError, APIError

from app.core.config import settings
from app.services.agent import simple_agent
from scripts.show_trace import _load_events


TRACE_DIR = Path("data/traces")


@dataclass(frozen=True)
class TrajectoryCase:
    name: str
    user_message: str
    expected_tools: list[str] = field(default_factory=list)
    final_contains: list[str] = field(default_factory=list)
    allow_tool_errors: bool = False


def _cases() -> list[TrajectoryCase]:
    return [
        TrajectoryCase(
            name="calculator_square",
            user_message="18 的平方是多少？",
            expected_tools=["calculator"],
            final_contains=["324"],
        ),
        TrajectoryCase(
            name="weather_single_city",
            user_message="北京今天热不热？",
            expected_tools=["weather"],
        ),
        TrajectoryCase(
            name="rag_project_summary",
            user_message="根据知识库总结一下这个项目的功能。",
            expected_tools=["rag"],
            allow_tool_errors=True,
        ),
    ]


def _latest_trace_after(start_time: float) -> Path | None:
    if not TRACE_DIR.exists():
        return None

    candidates = [
        path
        for path in TRACE_DIR.glob("*.jsonl")
        if path.stat().st_mtime >= start_time
    ]
    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)


def _tool_names(events: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for event in events:
        if event.get("event") != "tool_call_finished":
            continue
        tool_name = event.get("payload", {}).get("tool_name")
        if tool_name:
            names.append(tool_name)
    return names


def _tool_errors(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        event
        for event in events
        if event.get("event") == "tool_call_error"
    ]


def _final_answer(events: list[dict[str, Any]], fallback: str) -> str:
    for event in reversed(events):
        if event.get("event") == "trace_finished":
            final_answer = event.get("payload", {}).get("final_answer")
            if final_answer:
                return final_answer
    return fallback


def _contains_in_order(actual: list[str], expected: list[str]) -> bool:
    cursor = 0
    for item in actual:
        if cursor < len(expected) and item == expected[cursor]:
            cursor += 1
    return cursor == len(expected)


def _check_case(
    case: TrajectoryCase,
    answer: str,
    events: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    tools = _tool_names(events)
    tool_errors = _tool_errors(events)
    final_answer = _final_answer(events, answer)

    if not _contains_in_order(tools, case.expected_tools):
        errors.append(f"expected tools in order {case.expected_tools!r}, got {tools!r}")

    if tool_errors and not case.allow_tool_errors:
        errors.append(f"expected no tool errors, got {len(tool_errors)}")

    for text in case.final_contains:
        if text not in final_answer:
            errors.append(f"expected final answer to contain {text!r}, got {final_answer!r}")

    return not errors, errors


def run_case(case: TrajectoryCase) -> tuple[bool, list[str], Path | None, str]:
    start_time = time.time()
    answer = ""

    try:
        answer = "".join(simple_agent([{"role": "user", "content": case.user_message}]))
    except APIConnectionError as exc:
        return False, [f"could not connect to model service at {settings.llm_base_url!r}: {exc}"], None, answer
    except APIError as exc:
        return False, [f"model API error: {exc}"], None, answer

    trace_path = _latest_trace_after(start_time)
    if trace_path is None:
        return False, ["no trace file was generated"], None, answer

    events = _load_events(trace_path)
    ok, errors = _check_case(case, answer, events)
    return ok, errors, trace_path, answer


def run_eval(selected: str | None = None) -> int:
    cases = [case for case in _cases() if selected is None or case.name == selected]
    if not cases:
        print(f"No trajectory eval case named {selected!r}")
        return 2

    passed = 0
    for case in cases:
        print(f"\n[RUN] {case.name}")
        ok, errors, trace_path, answer = run_case(case)

        if ok:
            passed += 1
            print(f"[PASS] trace={trace_path}")
            continue

        print(f"[FAIL] trace={trace_path}")
        if answer:
            print(f"  answer={answer!r}")
        for error in errors:
            print(f"  - {error}")

    print(f"\nResult: {passed}/{len(cases)} passed")
    return 0 if passed == len(cases) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate full agent trajectories.")
    parser.add_argument("--case", help="Run one trajectory eval case by name.")
    args = parser.parse_args()

    raise SystemExit(run_eval(args.case))


if __name__ == "__main__":
    main()
