from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


TRACE_DIR = Path("data/traces")


def _latest_trace_path() -> Path | None:
    if not TRACE_DIR.exists():
        return None

    traces = sorted(
        TRACE_DIR.glob("*.jsonl"),
        key=lambda path: path.stat().st_mtime,
    )
    return traces[-1] if traces else None


def _resolve_trace_path(trace: str | None, latest: bool) -> Path:
    if latest:
        path = _latest_trace_path()
        if path is None:
            raise SystemExit("No trace files found in data/traces.")
        return path

    if not trace:
        raise SystemExit("Provide --latest, --trace-id, or a trace file path.")

    path = Path(trace)
    if path.exists():
        return path

    candidate = TRACE_DIR / f"{trace}.jsonl"
    if candidate.exists():
        return candidate

    raise SystemExit(f"Trace not found: {trace}")


def _load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON on line {line_number}: {exc}") from exc
    return events


def _compact(text: str | None, limit: int = 500) -> str:
    if not text:
        return ""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def _print_tool_calls(tool_calls: list[dict[str, Any]]) -> None:
    for tool_call in tool_calls:
        print(
            "  Tool call: "
            f"{tool_call.get('name')}({tool_call.get('arguments')}) "
            f"id={tool_call.get('id')}"
        )


def show_trace(path: Path) -> None:
    events = _load_events(path)
    if not events:
        print(f"Trace file is empty: {path}")
        return

    trace_id = events[0].get("trace_id", path.stem)
    print(f"Trace: {trace_id}")
    print(f"File: {path}")

    current_step: int | None = None

    for event in events:
        event_type = event.get("event")
        payload = event.get("payload", {})
        elapsed_ms = event.get("elapsed_ms")

        if event_type == "trace_started":
            print()
            print(f"User: {_compact(payload.get('user_message'), limit=1000)}")
            continue

        if event_type == "plan_created":
            print()
            print("Plan:")
            steps = payload.get("steps") or []
            if not steps:
                print("  (none)")
            for index, item in enumerate(steps, start=1):
                print(f"  {index}. {_compact(str(item), limit=300)}")
            continue

        step = payload.get("step")
        if step is not None and step != current_step:
            current_step = step
            print()
            print(f"Step {step}")

        if event_type == "llm_request":
            print(
                "  LLM request: "
                f"message_count={payload.get('message_count')}, "
                f"use_tools={payload.get('use_tools')}, "
                f"elapsed_ms={elapsed_ms}"
            )
        elif event_type == "llm_response":
            tool_calls = payload.get("tool_calls") or []
            print(
                "  LLM response: "
                f"tool_calls_count={payload.get('tool_calls_count')}, "
                f"elapsed_ms={elapsed_ms}"
            )
            if tool_calls:
                _print_tool_calls(tool_calls)
            assistant_content = _compact(payload.get("assistant_content"))
            if assistant_content:
                print(f"  Assistant: {assistant_content}")
        elif event_type == "tool_call_started":
            print(
                "  Tool started: "
                f"{payload.get('tool_name')}({payload.get('arguments')})"
            )
        elif event_type == "tool_call_finished":
            status = "ok" if payload.get("succeeded", True) else "error"
            print(
                "  Tool result: "
                f"{payload.get('tool_name')} [{status}] -> {_compact(payload.get('result'), limit=1000)}"
            )
        elif event_type == "tool_call_error":
            print(
                "  Tool error: "
                f"{payload.get('tool_name')} -> {payload.get('error')}"
            )
        elif event_type == "tool_call_skipped":
            print(
                "  Tool skipped: "
                f"{payload.get('tool_name')} reason={payload.get('reason')}"
            )
        elif event_type == "final_llm_request":
            print()
            print(
                "Final LLM request: "
                f"message_count={payload.get('message_count')}, "
                f"use_tools={payload.get('use_tools')}, "
                f"elapsed_ms={elapsed_ms}"
            )
        elif event_type == "trace_finished":
            print()
            print(f"Final answer: {_compact(payload.get('final_answer'), limit=1000)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an agent trace JSONL file.")
    parser.add_argument("trace", nargs="?", help="Trace id or path to a .jsonl trace file.")
    parser.add_argument("--latest", action="store_true", help="Show the latest trace.")
    args = parser.parse_args()

    show_trace(_resolve_trace_path(args.trace, args.latest))


if __name__ == "__main__":
    main()
