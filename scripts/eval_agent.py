from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models.planner import ToolDecision
from app.tools.decide import decide_tool


@dataclass(frozen=True)
class EvalCase:
    name: str
    prompt: str
    expected_tool: str | None
    expected_args: dict[str, str] = field(default_factory=dict)


def _contains(value: Any, expected: str) -> bool:
    return expected in str(value)


def _check_decision(case: EvalCase, decision: ToolDecision) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if decision.tool != case.expected_tool:
        errors.append(f"expected tool {case.expected_tool!r}, got {decision.tool!r}")

    for key, expected_value in case.expected_args.items():
        actual_value = decision.arguments.get(key)
        if actual_value is None:
            errors.append(f"missing argument {key!r}")
            continue

        if not _contains(actual_value, expected_value):
            errors.append(f"expected argument {key!r} to contain {expected_value!r}, got {actual_value!r}")

    return not errors, errors


def _cases() -> list[EvalCase]:
    return [
        EvalCase(
            name="calculator_square",
            prompt="18 的平方是多少？",
            expected_tool="calculator",
            expected_args={"expression": "18"},
        ),
        EvalCase(
            name="weather_single_city",
            prompt="北京今天热不热？",
            expected_tool="weather",
            expected_args={"city": "北京"},
        ),
        EvalCase(
            name="weather_compare_first_city",
            prompt="今天成都和乐山哪里的温度更高？",
            expected_tool="weather",
        ),
        EvalCase(
            name="weather_compare_missing_city_after_chengdu",
            prompt="""
Original user message:
今天成都和乐山哪里的温度更高？

Tool observations so far:
1. weather (success): City: 成都
Weather: Partly cloudy
Temperature: 33 C
Feels like: 47 C

Decide the next MCP tool call.
If this is a comparison question, make sure every item being compared has the needed data.
If the observations are enough to answer the original user message, return no tool.
""",
            expected_tool="weather",
            expected_args={"city": "乐山"},
        ),
        EvalCase(
            name="weather_compare_stop_after_both_cities",
            prompt="""
Original user message:
今天成都和乐山哪里的温度更高？

Tool observations so far:
1. weather (success): City: 成都
Weather: Partly cloudy
Temperature: 33 C
Feels like: 47 C
2. weather (success): City: 乐山
Weather: Cloudy
Temperature: 31 C
Feels like: 39 C

Decide the next MCP tool call.
If this is a comparison question, make sure every item being compared has the needed data.
If the observations are enough to answer the original user message, return no tool.
""",
            expected_tool=None,
        ),
        EvalCase(
            name="rag_knowledge_base",
            prompt="根据知识库总结一下这个项目的功能。",
            expected_tool="rag",
            expected_args={"query": "项目"},
        ),
    ]


def run_eval(selected: str | None = None) -> int:
    cases = [case for case in _cases() if selected is None or case.name == selected]
    if not cases:
        print(f"No eval case named {selected!r}")
        return 2

    passed = 0

    for case in cases:
        print(f"\n[RUN] {case.name}")
        decision = decide_tool(case.prompt)
        ok, errors = _check_decision(case, decision)

        if ok:
            passed += 1
            print(f"[PASS] tool={decision.tool!r} arguments={decision.arguments}")
            continue

        print(f"[FAIL] tool={decision.tool!r} arguments={decision.arguments}")
        for error in errors:
            print(f"  - {error}")

    print(f"\nResult: {passed}/{len(cases)} passed")
    return 0 if passed == len(cases) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate agent tool routing decisions.")
    parser.add_argument("--case", help="Run one eval case by name.")
    args = parser.parse_args()

    raise SystemExit(run_eval(args.case))


if __name__ == "__main__":
    main()
