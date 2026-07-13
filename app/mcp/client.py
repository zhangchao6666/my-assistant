import asyncio
import os
import sys
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar

from mcp import types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]
T = TypeVar("T")


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.server"],
        cwd=PROJECT_ROOT,
    )


def _run_async(coro_factory: Callable[[], Awaitable[T]]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())

    result: dict[str, T] = {}
    error: dict[str, BaseException] = {}

    def runner() -> None:
        try:
            result["value"] = asyncio.run(coro_factory())
        except BaseException as exc:
            error["value"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]

    return result["value"]


def _content_to_text(content: list[types.ContentBlock]) -> str:
    texts: list[str] = []
    for item in content:
        if isinstance(item, types.TextContent):
            texts.append(item.text)
    return "\n".join(texts).strip()


def _tool_to_dict(tool: types.Tool) -> dict[str, Any]:
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.inputSchema,
    }


async def _call_mcp_tool_async(tool_name: str, arguments: dict[str, Any]) -> str:
    with open(os.devnull, "w", encoding="utf-8") as errlog:
        async with stdio_client(_server_params(), errlog=errlog) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

    text = _content_to_text(result.content)
    if result.isError:
        raise RuntimeError(text or f"MCP tool failed: {tool_name}")

    return text


async def _list_mcp_tools_async() -> list[dict[str, Any]]:
    with open(os.devnull, "w", encoding="utf-8") as errlog:
        async with stdio_client(_server_params(), errlog=errlog) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()

    return [_tool_to_dict(tool) for tool in result.tools]


def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    return _run_async(lambda: _call_mcp_tool_async(tool_name, arguments))


@lru_cache(maxsize=1)
def list_mcp_tools() -> tuple[dict[str, Any], ...]:
    return tuple(_run_async(_list_mcp_tools_async))
