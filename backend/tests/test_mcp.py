import json
import sys
from unittest.mock import MagicMock

import pytest

from app.ai.mcp.adapter import format_mcp_content, json_schema_to_pydantic_model
from app.ai.mcp.manager import MCPManager, MCPTimeoutError, StdioMCPClient
from app.ai.tools.workspace import TOOL_CAPABILITY_TIERS


def test_mcp_config_loading_handles_missing_and_valid_files(tmp_path):
    missing = tmp_path / "does_not_exist.json"
    manager = MCPManager()
    assert manager.load_config(missing) == {"mcpServers": {}}

    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")
    assert manager.load_config(empty_file) == {"mcpServers": {}}

    valid_file = tmp_path / "mcp_servers.json"
    valid_file.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "mock": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": ["-m", "app.ai.mcp.mock_server"],
                    },
                    "disabled_srv": {
                        "transport": "stdio",
                        "command": "nonexistent_cmd",
                        "disabled": True,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    loaded = manager.load_config(valid_file)
    assert "mock" in loaded["mcpServers"]
    assert loaded["mcpServers"]["disabled_srv"]["disabled"] is True


def test_json_schema_to_pydantic_and_format_content():
    model = json_schema_to_pydantic_model(
        "sample-tool",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 5},
                "strict": {"type": "boolean", "default": False},
            },
            "required": ["query"],
        },
    )
    instance = model(query="hello")
    assert instance.query == "hello"
    assert instance.limit == 5
    assert instance.strict is False

    assert format_mcp_content({"content": [{"type": "text", "text": "ok"}]}) == "ok"
    with pytest.raises(RuntimeError, match="boom"):
        format_mcp_content({"isError": True, "content": [{"type": "text", "text": "boom"}]})


def test_mcp_manager_stdio_mock_server_lifecycle_and_fault_tolerance(tmp_path):
    cfg = tmp_path / "mcp_servers.json"
    cfg.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "mock": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": ["-m", "app.ai.mcp.mock_server"],
                        "timeout": 3.0,
                    },
                    "disabled_server": {
                        "transport": "stdio",
                        "command": "definitely_missing_binary_xyz",
                        "disabled": True,
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    manager = MCPManager(config_path=cfg)
    try:
        tools = manager.initialize_servers(cfg)
        assert "disabled_server" not in manager._clients
        assert "mock_echo" in tools
        assert "mock_add" in tools
        assert "mock_fail" in tools
        assert "mock_slow" in tools
        assert TOOL_CAPABILITY_TIERS["mock_echo"] == 1

        assert tools["mock_echo"].invoke({"message": "hello mcp"}) == "Echo: hello mcp"
        assert tools["mock_add"].invoke({"a": 2, "b": 3}) == "5"

        # Fault-tolerant tool error handling returns clean string instead of crashing
        fail_result = tools["mock_fail"].invoke({"reason": "simulated error"})
        assert "Error from MCP server 'mock'" in fail_result
        assert "simulated error" in fail_result

        # Shrink client timeout after handshake to test RPC timeout without slow waiting
        manager._clients["mock"].timeout = 0.25
        slow_result = tools["mock_slow"].invoke({"seconds": 1.5})
        assert "Error from MCP server 'mock'" in slow_result
        assert "timed out" in slow_result.lower()
    finally:
        manager.close()


def test_stdio_client_raises_timeout_directly():
    client = StdioMCPClient(
        server_name="mock-timeout",
        command=sys.executable,
        args=["-m", "app.ai.mcp.mock_server"],
        timeout=3.0,
    )
    try:
        client.connect()
        client.initialize()
        client.timeout = 0.25
        with pytest.raises(MCPTimeoutError):
            client.call_tool("mock_slow", {"seconds": 1.5})
    finally:
        client.close()


def test_mcp_manager_gracefully_skips_broken_server():
    manager = MCPManager()
    try:
        tools = manager.register_server(
            "broken",
            {
                "transport": "stdio",
                "command": "nonexistent_mcp_executable_12345",
                "args": [],
            },
        )
        assert tools == []
        unsupported = manager.register_server("bad_transport", {"transport": "grpc"})
        assert unsupported == []
    finally:
        manager.close()


def test_get_agent_tools_merges_and_isolates_mcp_failures(monkeypatch):
    from app.ai.graph import agent as agent_mod

    fake_mcp_tool = MagicMock()
    fake_mcp_tool.name = "custom_mcp_lookup"

    duplicate_builtin = MagicMock()
    duplicate_builtin.name = "read_workspace_file"

    monkeypatch.setattr(
        agent_mod.mcp_manager,
        "get_tools",
        lambda: [fake_mcp_tool, duplicate_builtin],
    )
    merged = agent_mod.get_agent_tools()
    names = [t.name for t in merged]
    assert "custom_mcp_lookup" in names
    assert names.count("read_workspace_file") == 1

    def _boom():
        raise RuntimeError("mcp offline")

    monkeypatch.setattr(agent_mod.mcp_manager, "get_tools", _boom)
    fallback = agent_mod.get_agent_tools()
    assert len(fallback) == len(agent_mod.tools)
