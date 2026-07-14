from collections.abc import Generator
from functools import lru_cache
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.mcp.client import list_mcp_tools
from app.prompts.system import CHAT_SYSTEM_PROMPT
from app.tools.function_calling import mcp_tools_to_openai_tools


client = OpenAI(
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
)


@lru_cache(maxsize=1)
def get_openai_tools() -> list[dict[str, Any]]:
    return mcp_tools_to_openai_tools(list_mcp_tools())


def _tool_kwargs(use_tools: bool) -> dict[str, Any]:
    if not use_tools:
        return {}

    return {
        "tools": get_openai_tools(),
        "tool_choice": "auto",
    }


class LLM:
    def chat(self, messages: list[dict], *, use_tools: bool = False) -> str:
        response = client.chat.completions.create(
            model=settings.chat_model,
            messages=messages,
            stream=False,
            **_tool_kwargs(use_tools),
        )
        return response.choices[0].message.content or ""

    def chat_message(self, messages: list[dict], *, use_tools: bool = False):
        response = client.chat.completions.create(
            model=settings.chat_model,
            messages=messages,
            stream=False,
            **_tool_kwargs(use_tools),
        )
        return response.choices[0].message

    def stream_chat(self, messages: list[dict], *, use_tools: bool = False) -> Generator[str, None, None]:
        stream = client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {
                    "role": "system",
                    "content": CHAT_SYSTEM_PROMPT,
                },
                *messages,
            ],
            stream=True,
            **_tool_kwargs(use_tools),
        )

        started = False

        for chunk in stream:
            content = chunk.choices[0].delta.content

            if not content:
                continue

            if not started:
                content = content.lstrip()
                if not content:
                    continue
                started = True

            if content:
                yield content
