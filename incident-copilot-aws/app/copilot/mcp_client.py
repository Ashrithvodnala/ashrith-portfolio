"""Start the MCP tool server as a subprocess and expose its tools to the agent."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager


@asynccontextmanager
async def mcp_tools():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "copilot.mcp_server"], env=dict(os.environ))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            tools = [
                {"name": t.name, "description": t.description or t.name, "input_schema": t.input_schema}
                for t in listed.tools
            ]

            async def call_tool(name: str, args: dict) -> str:
                result = await session.call_tool(name, args)
                text = "\n".join(c.text for c in result.content if getattr(c, "type", "") == "text")
                if result.is_error:
                    raise RuntimeError(text or "tool failed")
                return text

            yield tools, call_tool
