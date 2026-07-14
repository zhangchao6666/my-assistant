from collections.abc import Generator

from app.mcp.client import call_mcp_tool
from app.prompts.system import CHAT_SYSTEM_PROMPT
from app.services.llm import LLM
from app.tools.function_calling import parse_tool_call_arguments


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


def simple_agent(messages: list[dict]) -> Generator[str, None, None]:
    llm = LLM()
    working_messages = [
        {
            "role": "system",
            "content": CHAT_SYSTEM_PROMPT,
        },
        *messages,
    ]
    used_tool_calls: set[tuple[str, str]] = set()

    for step in range(MAX_AGENT_STEPS):
        assistant_message = llm.chat_message(working_messages, use_tools=True)
        tool_calls = assistant_message.tool_calls or []

        print(f"====AGENT STEP {step + 1}====")
        print(f"tool_calls_count={len(tool_calls)}")

        if not tool_calls:
            content = assistant_message.content or ""
            print(f"no tool_calls, assistant_content={_preview(content)!r}")
            if content:
                yield content
            return

        working_messages.append(_message_to_dict(assistant_message))

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = parse_tool_call_arguments(tool_call.function.arguments)
            tool_call_key = (tool_name, str(sorted(arguments.items())))

            print(f"tool={tool_name!r} arguments={arguments}")

            if tool_call_key in used_tool_calls:
                tool_result = f"Skipped repeated tool call: {tool_name} {arguments}"
            else:
                used_tool_calls.add(tool_call_key)
                try:
                    tool_result = call_mcp_tool(tool_name, arguments)
                except Exception as exc:
                    tool_result = f"MCP {tool_name} call failed: {exc}"

            print("====TOOL RESULT====")
            print(tool_result)

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
    yield from llm.stream_chat(working_messages, use_tools=False)
