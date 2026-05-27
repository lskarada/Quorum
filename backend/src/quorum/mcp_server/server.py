"""Quorum MCP stdio server exposing diagnose_case."""
from __future__ import annotations

import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .tools import (
    DIAGNOSE_CASE_INPUT_SCHEMA,
    DIAGNOSE_CASE_TOOL_NAME,
    diagnose_case_tool,
)

server = Server("quorum")


@server.list_tools()
async def _list_tools() -> list[Tool]:
    return [
        Tool(
            name=DIAGNOSE_CASE_TOOL_NAME,
            description="Run the Quorum diagnostic panel against a case presentation.",
            inputSchema=DIAGNOSE_CASE_INPUT_SCHEMA,
        )
    ]


@server.call_tool()
async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != DIAGNOSE_CASE_TOOL_NAME:
        raise ValueError(f"Unknown tool: {name}")
    result = await diagnose_case_tool(arguments)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
