"""Quorum exposed as an MCP server.

Any MCP-speaking agent (Claude Code, Claude Desktop, etc.) can call
the `diagnose_case` tool to get a structured differential.
"""
from __future__ import annotations

# TODO: the exact MCP Python SDK API surface (`mcp>=1.0.0`) uses decorator-based
# tool registration via `@server.list_tools()` and `@server.call_tool()`, not the
# imperative `server.add_tool()` shown in early design drafts. Wire it up against
# the installed SDK; see https://github.com/modelcontextprotocol/python-sdk for
# the current pattern.


async def main() -> None:
    """Run the MCP server over stdio (standard for local MCP)."""
    # TODO: import mcp.server.Server + mcp.server.stdio.stdio_server, register
    # the diagnose_case tool, and run the event loop over stdio.
    raise NotImplementedError


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
