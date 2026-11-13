"""
Model Context Protocol (MCP) Integration for GPTCraft.
"""
from app.ai.mcp.adapter import (
    json_schema_to_pydantic_model,
    format_mcp_content,
    mcp_tool_to_structured_tool,
)
from app.ai.mcp.manager import (
    BaseMCPClient,
    StdioMCPClient,
    SSEMCPClient,
    MCPManager,
    MCPError,
    MCPTimeoutError,
    MCPConnectionError,
    mcp_manager,
)

__all__ = [
    "json_schema_to_pydantic_model",
    "format_mcp_content",
    "mcp_tool_to_structured_tool",
    "BaseMCPClient",
    "StdioMCPClient",
    "SSEMCPClient",
    "MCPManager",
    "MCPError",
    "MCPTimeoutError",
    "MCPConnectionError",
    "mcp_manager",
]
