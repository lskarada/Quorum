"""Boot the MCP server over stdio."""
import asyncio

from quorum.mcp_server.server import main

if __name__ == "__main__":
    asyncio.run(main())
