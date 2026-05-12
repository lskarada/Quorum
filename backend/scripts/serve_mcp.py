"""Boot the MCP server over stdio."""
import asyncio

from quorum.mcp_server.server import main

if __name__ == "__main__":
    # TODO: this currently raises NotImplementedError until mcp_server/server.py
    # is wired against the installed `mcp>=1.0.0` Python SDK.
    asyncio.run(main())
