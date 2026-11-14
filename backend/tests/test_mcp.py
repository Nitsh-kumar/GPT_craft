import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.ai.mcp.adapter import (
    format_mcp_content,
    json_schema_to_pydantic_model,
    mcp_tool_to_structured_tool,
)
from app.ai.mcp.manager import MCPManager, MCPTimeoutError, StdioMCPClient
from app.ai.tools.workspace import MAX_TOOL_OUTPUT_CHARS, TOOL_CAPABILITY_TIERS, get_tool_tier


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
                        "timeout": 10.0,
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
        assert TOOL_CAPABILITY_TIERS["mock_echo"] == 2
        assert get_tool_tier("mock_echo") == 2

        with patch(
            "app.ai.mcp.adapter.interrupt",
            return_value={"decision": "approve"},
        ):
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
        timeout=10.0,
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


def test_default_mcp_config_disables_mock_server_and_blocks_production_spawn(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("MCP_SERVERS_CONFIG_PATH", raising=False)
    monkeypatch.delenv("MCP_ENABLE_MOCK_SERVER", raising=False)

    backend_dir = Path(__file__).resolve().parents[1]
    default_cfg_path = backend_dir / "mcp_servers.json"

    manager = MCPManager(config_path=default_cfg_path)
    try:
        config = manager.load_config()
        assert config["mcpServers"]["filesystem"]["disabled"] is True

        tools = manager.initialize_servers()
        assert tools == {}
        assert manager._clients == {}
    finally:
        manager.close()

    # Even if a config omits "disabled": true (or opt-in env is set),
    # production environment variables must prevent spawning mock_server.
    unsafe_cfg = tmp_path / "prod_mcp_servers.json"
    unsafe_cfg.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "mock": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": ["-m", "app.ai.mcp.mock_server"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("MCP_ENABLE_MOCK_SERVER", "true")
    prod_manager = MCPManager(config_path=unsafe_cfg)
    try:
        prod_tools = prod_manager.initialize_servers(unsafe_cfg)
        assert prod_tools == {}
        assert prod_manager._clients == {}

        direct_tools = prod_manager.register_server(
            "mock",
            {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "app.ai.mcp.mock_server"],
            },
        )
        assert direct_tools == []
    finally:
        prod_manager.close()


def test_mcp_tools_default_to_tier_2_and_enforce_hitl_gating(monkeypatch):
    monkeypatch.delitem(TOOL_CAPABILITY_TIERS, "ext_unannotated_action", raising=False)
    monkeypatch.delitem(TOOL_CAPABILITY_TIERS, "ext_invalid_tier_action", raising=False)

    fake_client = MagicMock()
    fake_client.list_tools.return_value = [
        {
            "name": "ext_unannotated_action",
            "description": "External unannotated MCP tool",
            "inputSchema": {
                "type": "object",
                "properties": {"target": {"type": "string"}},
                "required": ["target"],
            },
        }
    ]
    fake_client.call_tool.return_value = {
        "content": [{"type": "text", "text": "executed"}],
        "isError": False,
    }

    with patch("app.ai.mcp.manager.StdioMCPClient", return_value=fake_client):
        manager = MCPManager()
        tools = manager.register_server(
            "external_unannotated",
            {"transport": "stdio", "command": "npx", "args": ["some-mcp-server"]},
        )

    assert len(tools) == 1
    tool = tools[0]
    assert TOOL_CAPABILITY_TIERS["ext_unannotated_action"] == 2
    assert get_tool_tier("ext_unannotated_action") == 2

    # Direct invocation outside a LangGraph pregel runner must fail closed (never auto-approve)
    with pytest.raises((RuntimeError, KeyError)):
        tool.invoke({"target": "prod-db"})
    fake_client.call_tool.assert_not_called()

    # Missing, non-dict, or unknown decisions must fail closed without calling client
    for bad_payload in (None, {}, {"decision": ""}, {"decision": "defer"}):
        with patch("app.ai.mcp.adapter.interrupt", return_value=bad_payload):
            blocked = tool.invoke({"target": "prod-db"})
            assert "Action rejected" in blocked
            fake_client.call_tool.assert_not_called()

    # Rejection via HITL interrupt prevents underlying client.call_tool execution
    with patch(
        "app.ai.mcp.adapter.interrupt",
        return_value={"decision": "reject", "feedback": "Needs manual verification"},
    ) as mock_interrupt:
        rejected = tool.invoke({"target": "prod-db"})
        assert mock_interrupt.called
        payload = mock_interrupt.call_args[0][0]
        assert payload["tool"] == "ext_unannotated_action"
        assert payload["tier"] == 2
        assert payload["parameters"] == {"target": "prod-db"}
        assert "Action rejected by user" in rejected
        assert "Needs manual verification" in rejected
        fake_client.call_tool.assert_not_called()

    # Modification via HITL interrupt updates forwarded parameters
    with patch(
        "app.ai.mcp.adapter.interrupt",
        return_value={"decision": "modify", "modifiedParams": {"target": "staging-db"}},
    ):
        modified = tool.invoke({"target": "prod-db"})
        assert modified == "executed"
        fake_client.call_tool.assert_called_once_with(
            "ext_unannotated_action", {"target": "staging-db"}
        )

    # Invalid tier configuration safely falls back to Tier 2
    fake_client_invalid = MagicMock()
    fake_client_invalid.list_tools.return_value = [
        {"name": "ext_invalid_tier_action", "inputSchema": {"type": "object"}}
    ]
    with patch("app.ai.mcp.manager.StdioMCPClient", return_value=fake_client_invalid):
        MCPManager().register_server(
            "external_invalid_tier",
            {"transport": "stdio", "command": "npx", "tier": "invalid"},
        )
    assert TOOL_CAPABILITY_TIERS["ext_invalid_tier_action"] == 2
    assert get_tool_tier("ext_invalid_tier_action") == 2


def test_mcp_tier_2_langgraph_interrupt_and_tier_1_explicit_override(monkeypatch):
    from langchain_core.messages import AIMessage
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import END, START, MessagesState, StateGraph
    from langgraph.prebuilt import ToolNode
    from langgraph.types import Command

    monkeypatch.delitem(TOOL_CAPABILITY_TIERS, "ext_tier2_write", raising=False)
    monkeypatch.delitem(TOOL_CAPABILITY_TIERS, "ext_tier1_read", raising=False)

    tier2_client = MagicMock()
    tier2_client.list_tools.return_value = [
        {
            "name": "ext_tier2_write",
            "description": "Mutating external MCP call",
            "inputSchema": {
                "type": "object",
                "properties": {"item": {"type": "string"}},
                "required": ["item"],
            },
        }
    ]
    tier2_client.call_tool.return_value = {
        "content": [{"type": "text", "text": "wrote item"}],
        "isError": False,
    }

    tier1_client = MagicMock()
    tier1_client.list_tools.return_value = [
        {
            "name": "ext_tier1_read",
            "description": "Read-only external MCP lookup",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ]
    tier1_client.call_tool.return_value = {
        "content": [{"type": "text", "text": "R" * 5500}],
        "isError": False,
    }

    manager = MCPManager()
    with patch("app.ai.mcp.manager.StdioMCPClient", return_value=tier2_client):
        tier2_tools = manager.register_server(
            "unannotated_srv",
            {"transport": "stdio", "command": "ext-write"},
        )
    with patch("app.ai.mcp.manager.StdioMCPClient", return_value=tier1_client):
        tier1_tools = manager.register_server(
            "explicit_readonly_srv",
            {"transport": "stdio", "command": "ext-read", "tier": 1},
        )

    assert TOOL_CAPABILITY_TIERS["ext_tier2_write"] == 2
    assert TOOL_CAPABILITY_TIERS["ext_tier1_read"] == 1

    # Direct mcp_tool_to_structured_tool default is also Tier 2
    direct_default = mcp_tool_to_structured_tool(
        client=tier2_client,
        tool_info={"name": "ext_direct_default", "inputSchema": {"type": "object"}},
        server_name="direct",
    )
    assert TOOL_CAPABILITY_TIERS[direct_default.name] == 2
    monkeypatch.delitem(TOOL_CAPABILITY_TIERS, direct_default.name, raising=False)

    # Verify Tier 2 interrupts inside LangGraph before executing, while Tier 1 auto-executes
    builder = StateGraph(MessagesState)
    builder.add_node("tools", ToolNode(tier2_tools + tier1_tools))
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    graph = builder.compile(checkpointer=InMemorySaver())

    # 1. Tier 2 default tool triggers interrupt before calling underlying MCP client
    t2_cfg = {"configurable": {"thread_id": "mcp-tier2-test"}}
    interrupted = graph.invoke(
        {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "call_t2", "name": "ext_tier2_write", "args": {"item": "doc1"}}
                    ],
                )
            ]
        },
        config=t2_cfg,
    )
    assert "__interrupt__" in interrupted
    intr_val = interrupted["__interrupt__"][0].value
    assert intr_val["tool"] == "ext_tier2_write"
    assert intr_val["tier"] == 2
    assert intr_val["parameters"] == {"item": "doc1"}
    tier2_client.call_tool.assert_not_called()

    # Resuming with approval executes the MCP tool
    resumed = graph.invoke(Command(resume={"decision": "approve"}), config=t2_cfg)
    assert "__interrupt__" not in resumed
    tier2_client.call_tool.assert_called_once_with("ext_tier2_write", {"item": "doc1"})
    assert resumed["messages"][-1].content == "wrote item"

    # 2. Explicit Tier 1 tool auto-executes cleanly with 4,000-char truncation
    t1_cfg = {"configurable": {"thread_id": "mcp-tier1-test"}}
    t1_result = graph.invoke(
        {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "call_t1", "name": "ext_tier1_read", "args": {"query": "docs"}}
                    ],
                )
            ]
        },
        config=t1_cfg,
    )
    assert "__interrupt__" not in t1_result
    tier1_client.call_tool.assert_called_once_with("ext_tier1_read", {"query": "docs"})
    out_content = t1_result["messages"][-1].content
    assert len(out_content) <= MAX_TOOL_OUTPUT_CHARS
    assert "[Truncated to 4,000 chars]" in out_content


def test_agent_studio_stream_emits_approval_card_for_default_tier_2_mcp_tool(
    client, monkeypatch
):
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    from app.ai.graph import agent as agent_mod
    from tests.fakes import AgentToolFake

    monkeypatch.delitem(TOOL_CAPABILITY_TIERS, "ext_agent_mcp_call", raising=False)

    fake_client = MagicMock()
    fake_client.list_tools.return_value = [
        {
            "name": "ext_agent_mcp_call",
            "description": "External MCP mutation",
            "inputSchema": {
                "type": "object",
                "properties": {"payload": {"type": "string"}},
                "required": ["payload"],
            },
        }
    ]
    fake_client.call_tool.return_value = {
        "content": [{"type": "text", "text": "remote mcp ok"}],
        "isError": False,
    }

    with patch("app.ai.mcp.manager.StdioMCPClient", return_value=fake_client):
        mcp_tools = MCPManager().register_server(
            "ext_agent_srv",
            {"transport": "stdio", "command": "ext-mcp"},
        )

    assert len(mcp_tools) == 1
    assert get_tool_tier("ext_agent_mcp_call") == 2

    class _McpAgentFake(AgentToolFake):
        def bind_tools(self, tools, **kwargs):
            return _McpAgentFake(
                mode=self.mode,
                model_name=self.model_name,
                bound_tools=list(tools),
                failure=self.failure,
            )

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            if (
                self.mode == "agent"
                and self.bound_tools
                and messages
                and getattr(messages[-1], "type", "") == "human"
            ):
                msg = AIMessage(
                    content="Calling external MCP tool.",
                    tool_calls=[
                        {
                            "name": "ext_agent_mcp_call",
                            "args": {"payload": "hello"},
                            "id": "call_mcp_1",
                        }
                    ],
                    usage_metadata={"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
                )
                return ChatResult(generations=[ChatGeneration(message=msg)])
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    monkeypatch.setattr(
        agent_mod,
        "get_llm",
        lambda **kwargs: _McpAgentFake(
            mode=(kwargs.get("mode") or "standard").lower(),
            model_name=kwargs.get("model_id") or "openai/gpt-oss-20b",
        ),
    )
    monkeypatch.setattr(agent_mod.mcp_manager, "get_tools", lambda: mcp_tools)

    reg = client.post(
        "/auth/register",
        json={"name": "MCP Tester", "email": "mcp_studio@example.com", "password": "password123"},
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['accessToken']}"}

    def _parse_sse(raw: str):
        events = []
        for block in raw.replace("\r\n", "\n").split("\n\n"):
            block = block.strip()
            if not block:
                continue
            ev = None
            data_lines = []
            for line in block.split("\n"):
                if line.startswith("event:"):
                    ev = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[len("data:"):].strip())
            if data_lines:
                events.append({"event": ev, "data": json.loads("\n".join(data_lines))})
        return events

    stream_res = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Trigger external MCP tool", "mode": "agent"},
    )
    assert stream_res.status_code == 200
    events = _parse_sse(stream_res.text)
    action_calls = [e["data"] for e in events if e["event"] == "action_call"]
    approvals = [e["data"] for e in events if e["event"] == "approval_required"]
    dones = [e["data"] for e in events if e["event"] == "done"]

    assert len(action_calls) == 1
    assert action_calls[0]["tool"] == "ext_agent_mcp_call"
    assert action_calls[0]["tier"] == 2

    assert len(approvals) == 1
    assert approvals[0]["tool"] == "ext_agent_mcp_call"
    assert approvals[0]["tier"] == 2
    assert approvals[0]["parameters"] == {"payload": "hello"}
    assert dones[-1]["status"] == "interrupted"
    fake_client.call_tool.assert_not_called()

    # Approving resumes execution and invokes the external MCP client
    approve_res = client.post(
        "/chat/approval",
        headers=headers,
        json={"actionId": approvals[0]["actionId"], "decision": "approve"},
    )
    assert approve_res.status_code == 200
    resume_events = _parse_sse(approve_res.text)
    resume_results = [e["data"] for e in resume_events if e["event"] == "action_result"]
    resume_dones = [e["data"] for e in resume_events if e["event"] == "done"]

    fake_client.call_tool.assert_called_once_with("ext_agent_mcp_call", {"payload": "hello"})
    assert len(resume_results) >= 1
    assert "remote mcp ok" in resume_results[0]["output"]
    assert resume_dones[-1]["status"] == "completed"
