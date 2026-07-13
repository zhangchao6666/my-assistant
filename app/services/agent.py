from collections.abc import Generator

from app.models.tool import ToolResult
from app.prompts.tool_result import build_tool_result_prompt
from app.services.llm import LLM
from app.tools.decide import decide_tool
from app.tools.execute_tool import execute_tool


MAX_AGENT_STEPS = 4


def _format_observations(observations: list[ToolResult]) -> str:
    lines: list[str] = []
    for index, observation in enumerate(observations, start=1):
        status = "success" if observation.matched else "failed"
        content = observation.content or observation.message or ""
        lines.append(f"{index}. {observation.tool_name} ({status}): {content}")
    return "\n".join(lines)


def _build_tool_decision_input(user_message: str, observations: list[ToolResult]) -> str:
    if not observations:
        return f"""
Original user message:
{user_message}

No tool observations yet.
Choose the first MCP tool call if one is needed.
"""

    return f"""
Original user message:
{user_message}

Tool observations so far:
{_format_observations(observations)}

Decide the next MCP tool call.
If this is a comparison question, make sure every item being compared has the needed data.
If a previous tool was irrelevant or failed, choose a better tool instead of stopping.
If the observations are enough to answer the original user message, return no tool.
"""


def simple_agent(messages: list[dict]) -> Generator[str, None, None]:
    llm = LLM()
    user_message = messages[-1]["content"]
    observations: list[ToolResult] = []
    used_tool_calls: set[tuple[str, str]] = set()

    for step in range(MAX_AGENT_STEPS):
        decision_input = _build_tool_decision_input(user_message, observations)
        decision = decide_tool(decision_input)

        print(f"====AGENT STEP {step + 1}====")
        print(decision)

        if decision.tool is None:
            break

        tool_call_key = (decision.tool, str(sorted(decision.arguments.items())))
        if tool_call_key in used_tool_calls:
            print("Repeated tool call detected; stopping agent loop.")
            break
        used_tool_calls.add(tool_call_key)

        tool_result = execute_tool(decision)
        if not tool_result.matched:
            print("====TOOL FAILED====")
            print(tool_result)
            observations.append(tool_result)
            continue

        print("====TOOL RESULT====")
        print(tool_result)
        observations.append(tool_result)

    successful_observations = [observation for observation in observations if observation.matched]
    if successful_observations:
        final_tool_result = ToolResult(
            matched=True,
            tool_name="agent_observations",
            content=_format_observations(successful_observations),
        )
        prompt = build_tool_result_prompt(
            user_message=user_message,
            tool_result=final_tool_result,
        )

        yield from llm.stream_chat([
            {
                "role": "user",
                "content": prompt,
            }
        ])
        return

    yield from llm.stream_chat(messages)
