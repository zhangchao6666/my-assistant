from collections.abc import Generator
from functools import lru_cache
from typing import Any

from app.mcp.client import call_mcp_tool
from app.prompts.system import CHAT_SYSTEM_PROMPT
from app.services.llm import LLM, get_openai_tools
from app.services.planner import build_plan
from app.services.tracing import AgentTrace
from app.tools.function_calling import parse_tool_call_arguments_with_error


MAX_AGENT_STEPS = 4


def _message_to_dict(message) -> dict:
    return message.model_dump(exclude_none=True)


def _tool_result_message(tool_call_id: str, tool_name: str, content: str) -> dict:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": content,
    }


def _preview(text: str, limit: int = 300) -> str:
    compact = text.replace("\n", " ").strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def _format_plan(steps: list[str]) -> str:
    if not steps:
        return "No explicit plan was created."

    lines = ["Plan for the user goal:"]
    for index, step in enumerate(steps, start=1):
        lines.append(f"{index}. {step}")
    lines.append("Use the plan as guidance, but adapt if tool results show a better path.")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _tool_parameter_schemas() -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for tool in get_openai_tools():
        function = tool["function"]
        schemas[function["name"]] = function.get("parameters", {})
    return schemas


def _validate_tool_call(tool_name: str, arguments: dict[str, Any]) -> str | None:
    schemas = _tool_parameter_schemas()
    schema = schemas.get(tool_name)
    if schema is None:
        return f"Unknown tool: {tool_name}. Choose one of: {', '.join(schemas)}."

    missing = [
        key
        for key in schema.get("required", [])
        if key not in arguments or arguments[key] is None or arguments[key] == ""
    ]
    if missing:
        return f"Missing required argument(s) for {tool_name}: {', '.join(missing)}."

    return None


def _tool_error_message(error: str) -> str:
    return (
        "Tool call error: "
        f"{error} "
        "Fix the tool name or arguments and try again if a tool is still needed. "
        "If enough information is available, answer the user directly."
    )


def _execute_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    used_tool_calls: set[tuple[str, str]],
) -> tuple[str, str | None, bool]:
    tool_call_key = (tool_name, str(sorted(arguments.items())))

    validation_error = _validate_tool_call(tool_name, arguments)
    if validation_error:
        return _tool_error_message(validation_error), validation_error, False

    if tool_call_key in used_tool_calls:
        error = f"Repeated tool call: {tool_name} {arguments}."
        return _tool_error_message(error), error, False

    used_tool_calls.add(tool_call_key)
    try:
        return call_mcp_tool(tool_name, arguments), None, True
    except Exception as exc:
        error = f"MCP {tool_name} call failed: {exc}"
        return _tool_error_message(error), error, False


def simple_agent(messages: list[dict]) -> Generator[str, None, None]:
    llm = LLM()
    user_message = messages[-1]["content"]
    trace = AgentTrace(user_message=user_message)
    print(f"====TRACE ID {trace.trace_id}====")
    plan_steps = build_plan(user_message)
    trace.event(
        "plan_created",
        {
            "steps": plan_steps,
        },
    )

    working_messages = [
        {
            "role": "system",
            "content": CHAT_SYSTEM_PROMPT,
        },
        {
            "role": "system",
            "content": _format_plan(plan_steps),
        },
        *messages,
    ]
    used_tool_calls: set[tuple[str, str]] = set()

    for step in range(MAX_AGENT_STEPS):
        trace.event(
            "llm_request",
            {
                "step": step + 1,
                "message_count": len(working_messages),
                "use_tools": True,
            },
        )
        assistant_message = llm.chat_message(working_messages, use_tools=True)
        tool_calls = assistant_message.tool_calls or []

        print(f"====AGENT STEP {step + 1}====")
        print(f"tool_calls_count={len(tool_calls)}")
        trace.event(
            "llm_response",
            {
                "step": step + 1,
                "assistant_content": assistant_message.content,
                "tool_calls_count": len(tool_calls),
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    }
                    for tool_call in tool_calls
                ],
            },
        )

        if not tool_calls:
            content = assistant_message.content or ""
            print(f"no tool_calls, assistant_content={_preview(content)!r}")
            if content:
                trace.finish(final_answer=content)
                yield content
            return

        working_messages.append(_message_to_dict(assistant_message))

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments, parse_error = parse_tool_call_arguments_with_error(tool_call.function.arguments)

            print(f"tool={tool_name!r} arguments={arguments}")
            trace.event(
                "tool_call_started",
                {
                    "step": step + 1,
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "raw_arguments": tool_call.function.arguments,
                },
            )

            if parse_error:
                tool_result = _tool_error_message(parse_error)
                tool_error = parse_error
                succeeded = False
            else:
                tool_result, tool_error, succeeded = _execute_tool_call(
                    tool_name,
                    arguments,
                    used_tool_calls,
                )

            if tool_error:
                trace.event(
                    "tool_call_error",
                    {
                        "step": step + 1,
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "error": tool_error,
                    },
                )

            print("====TOOL RESULT====")
            print(tool_result)
            trace.event(
                "tool_call_finished",
                {
                    "step": step + 1,
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": tool_result,
                    "succeeded": succeeded,
                },
            )

            working_messages.append(
                _tool_result_message(
                    tool_call_id=tool_call.id,
                    tool_name=tool_name,
                    content=tool_result,
                )
            )

    final_prompt = {
        "role": "user",
        "content": "Use the tool results above to answer the original user question. Do not call more tools.",
    }
    working_messages.append(final_prompt)
    chunks: list[str] = []
    trace.event(
        "final_llm_request",
        {
            "message_count": len(working_messages),
            "use_tools": False,
        },
    )
    for chunk in llm.stream_chat(working_messages, use_tools=False):
        chunks.append(chunk)
        yield chunk
    trace.finish(final_answer="".join(chunks).strip())
