"""MCP discovery agent — finds and invokes MCP tools registered in the Agent Registry.

Adapted from the original discovery_agent_demo to share auth/registry helpers
with the rest of the agent_marketplace_demo.
"""

import os
import sys
from pathlib import Path

# Allow importing the shared common/ package when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

from common.auth import get_dynamic_headers
from common.registry_client import get_registry, parent_path

registry = get_registry()

registry_mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://agentregistry.googleapis.com/mcp",
        headers=get_dynamic_headers(),
    ),
    tool_name_prefix="registry",
    header_provider=get_dynamic_headers,
)


async def call_dynamic_mcp_tool(
    mcp_server_name: str,
    tool_name: str,
    tool_args: dict,
    tool_context: ToolContext,
) -> dict:
    """Call a tool on an MCP server discovered in the Agent Registry."""
    toolset = registry.get_mcp_toolset(mcp_server_name)
    tools = await toolset.get_tools()
    for tool in tools:
        if tool.name == tool_name or tool.name.endswith(f"_{tool_name}"):
            return await tool.run_async(args=tool_args, tool_context=tool_context)
    return {"error": f"Tool '{tool_name}' not found on '{mcp_server_name}'"}


DISCOVERY_INSTRUCTION = f"""You are the Dynamic Discovery and Execution Agent.
Your goal is to help users find and run tools dynamically from the Google Cloud Agent Registry.

Registry parent: {parent_path()}

Use `registry_search_mcp_servers` / `registry_list_mcp_servers` to find servers,
`registry_get_mcp_server` to inspect them, and `call_dynamic_mcp_tool` to invoke
a specific tool on a discovered server.
"""

root_agent = LlmAgent(
    # Gemini 3 Flash preview — consistent with the other agents in this demo.
    model=Gemini(model="gemini-3-flash-preview"),
    name="discovery_agent",
    static_instruction=DISCOVERY_INSTRUCTION,
    tools=[registry_mcp_toolset, call_dynamic_mcp_tool],
)
