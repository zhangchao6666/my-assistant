from collections.abc import Generator

from app.prompts.tool_result import build_tool_result_prompt
from app.services.llm import LLM
from app.tools.decide import decide_tool
from app.tools.rag import rag_tool
from app.tools.execute_tool import execute_tool

def simple_agent(messages: list[dict]) -> Generator[str, None, None]:
    llm = LLM()

    user_message = messages[-1]["content"]
    decision = decide_tool(messages)

    print(decision)

    tool_result = execute_tool(decision)
    
    if not tool_result.matched:
        tool_result = rag_tool(user_message)
    
    if tool_result.matched:
        print("====TOOL RESULT====")
        print(tool_result)

        prompt = build_tool_result_prompt(
            user_message=user_message,
            tool_result=tool_result,
        )

        yield from llm.stream_chat([
            {
                "role": "user",
                "content": prompt,
            }
        ])
        return

    yield from llm.stream_chat(messages)

