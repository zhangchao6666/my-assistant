import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from mcp import types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _content_to_text(content: list[types.ContentBlock]) -> str:
    texts: list[str] = []
    for item in content:
        if isinstance(item, types.TextContent):
            texts.append(item.text)
    return "\n".join(texts).strip()


async def _call_mcp_tool_async(tool_name: str, arguments: dict[str, Any]) -> str:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.server"],
        cwd=PROJECT_ROOT,
    )

    with open(os.devnull, "w", encoding="utf-8") as errlog:
        async with stdio_client(server_params, errlog=errlog) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

    text = _content_to_text(result.content)
    if result.isError:
        raise RuntimeError(text or f"MCP tool failed: {tool_name}")

    return text


def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    return asyncio.run(_call_mcp_tool_async(tool_name, arguments))

