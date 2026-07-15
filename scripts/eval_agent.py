from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openai import APIConnectionError, APIError

from app.core.config import settings
from app.prompts.system import CHAT_SYSTEM_PROMPT
from app.services.llm import LLM
from app.tools.function_calling import parse_tool_call_arguments


@dataclass(frozen=True)
class ExpectedToolCall:
    name: str
    arguments: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalCase:
    name: str
    messages: list[dict[str, Any]]
    expected_tool_calls: list[ExpectedToolCall]


def _contains(value: Any, expected: str) -> bool:
    return expected in str(value)


def _assistant_message(tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": tool_calls,
    }


def _tool_call(call_id: str, name: str, arguments_json: str) -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": arguments_json,
        },
    }


def _tool_result(call_id: str, name: str, content: str) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "name": name,
        "content": content,
    }


def _cases() -> list[EvalCase]:
    chengdu_call = _tool_call("call_chengdu", "weather", '{"city":"成都"}')
    leshan_call = _tool_call("call_leshan", "weather", '{"city":"乐山"}')

    return [
        EvalCase(
            name="calculator_square",
            messages=[{"role": "user", "content": "18 的平方是多少？"}],
            expected_tool_calls=[
                ExpectedToolCall("calculator", {"expression": "18"}),
            ],
        ),
        EvalCase(
            name="weather_single_city",
            messages=[{"role": "user", "content": "北京今天热不热？"}],
            expected_tool_calls=[
                ExpectedToolCall("weather", {"city": "北京"}),
            ],
        ),
        EvalCase(
            name="weather_compare_first_step",
            messages=[{"role": "user", "content": "今天成都和乐山哪里的温度更高？"}],
            expected_tool_calls=[
                ExpectedToolCall("weather"),
            ],
        ),
        EvalCase(
            name="weather_compare_missing_city_after_chengdu",
            messages=[
                {"role": "user", "content": "今天成都和乐山哪里的温度更高？"},
                _assistant_message([chengdu_call]),
                _tool_result(
                    "call_chengdu",
                    "weather",
                    "City: 成都\nWeather: Partly cloudy\nTemperature: 33 C\nFeels like: 47 C",
                ),
            ],
            expected_tool_calls=[
                ExpectedToolCall("weather", {"city": "乐山"}),
            ],
        ),
        EvalCase(
            name="weather_compare_stop_after_both_cities",
            messages=[
                {"role": "user", "content": "今天成都和乐山哪里的温度更高？"},
                _assistant_message([chengdu_call]),
                _tool_result(
                    "call_chengdu",
                    "weather",
                    "City: 成都\nWeather: Partly cloudy\nTemperature: 33 C\nFeels like: 47 C",
                ),
                _assistant_message([leshan_call]),
                _tool_result(
                    "call_leshan",
                    "weather",
                    "City: 乐山\nWeather: Cloudy\nTemperature: 31 C\nFeels like: 39 C",
                ),
            ],
            expected_tool_calls=[],
        ),
        EvalCase(
            name="rag_knowledge_base",
            messages=[{"role": "user", "content": "根据知识库总结一下这个项目的功能。"}],
            expected_tool_calls=[
                ExpectedToolCall("rag", {"query": "项目"}),
            ],
        ),
    ]


def _actual_tool_calls(message) -> list[tuple[str, dict[str, Any]]]:
    calls = []
    for tool_call in message.tool_calls or []:
        calls.append(
            (
                tool_call.function.name,
                parse_tool_call_arguments(tool_call.function.arguments),
            )
        )
    return calls


def _matches_expected(actual: tuple[str, dict[str, Any]], expected: ExpectedToolCall) -> tuple[bool, list[str]]:
    tool_name, arguments = actual
    errors: list[str] = []

    if tool_name != expected.name:
        errors.append(f"expected tool {expected.name!r}, got {tool_name!r}")

    for key, expected_value in expected.arguments.items():
        actual_value = arguments.get(key)
        if actual_value is None:
            errors.append(f"missing argument {key!r}")
            continue

        if not _contains(actual_value, expected_value):
            errors.append(f"expected argument {key!r} to contain {expected_value!r}, got {actual_value!r}")

    return not errors, errors


def _check_case(case: EvalCase, actual_calls: list[tuple[str, dict[str, Any]]]) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not case.expected_tool_calls:
        if actual_calls:
            errors.append(f"expected no tool calls, got {actual_calls!r}")
        return not errors, errors

    if len(actual_calls) < len(case.expected_tool_calls):
        errors.append(f"expected at least {len(case.expected_tool_calls)} tool call(s), got {len(actual_calls)}")

    for index, expected in enumerate(case.expected_tool_calls):
        if index >= len(actual_calls):
            break
        ok, call_errors = _matches_expected(actual_calls[index], expected)
        if not ok:
            errors.extend(f"call {index + 1}: {error}" for error in call_errors)

    return not errors, errors


def run_eval(selected: str | None = None) -> int:
    cases = [case for case in _cases() if selected is None or case.name == selected]
    if not cases:
        print(f"No eval case named {selected!r}")
        return 2

    llm = LLM()
    passed = 0

    for case in cases:
        print(f"\n[RUN] {case.name}")
        messages = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            *case.messages,
        ]

        try:
            message = llm.chat_message(messages, use_tools=True)
        except APIConnectionError as exc:
            print(f"[ERROR] Could not connect to model service at {settings.llm_base_url!r}: {exc}")
            return 2
        except APIError as exc:
            print(f"[ERROR] Model API error: {exc}")
            return 2

        actual_calls = _actual_tool_calls(message)
        ok, errors = _check_case(case, actual_calls)

        if ok:
            passed += 1
            print(f"[PASS] tool_calls={actual_calls}")
            continue

        print(f"[FAIL] tool_calls={actual_calls}")
        if message.content:
            print(f"  assistant_content={message.content!r}")
        for error in errors:
            print(f"  - {error}")

    print(f"\nResult: {passed}/{len(cases)} passed")
    return 0 if passed == len(cases) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate function-calling tool decisions.")
    parser.add_argument("--case", help="Run one eval case by name.")
    args = parser.parse_args()

    raise SystemExit(run_eval(args.case))


if __name__ == "__main__":
    main()
