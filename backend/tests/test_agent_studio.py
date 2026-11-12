import json
import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_suite.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-ci-harness"
os.environ["GROQ_API_KEY"] = "test-groq-api-key"

from app.main import app, seed_default_plan
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.ai.llm import CRAFT_MODES
from app.ai.prompts import MODE_TEMPERATURES

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    os.environ["GROQ_API_KEY"] = "test-groq-api-key"
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_default_plan()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def cleanup_sqlite_file():
    yield
    engine.dispose()
    for db_file in ("test_suite.db", "backend/test_suite.db"):
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


def register_user(email="agent@example.com"):
    res = client.post(
        "/auth/register",
        json={"name": "Agent Tester", "email": email, "password": "password123"},
    )
    assert res.status_code == 201
    return res.json()["accessToken"]


def parse_sse_blocks(raw_body: str):
    events = []
    normalized = raw_body.replace("\r\n", "\n")
    for block in normalized.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event_name = None
        data_lines = []
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())
        if data_lines:
            payload = json.loads("\n".join(data_lines))
            events.append({"event": event_name, "data": payload})
    return events


def test_craft_modes_includes_agent_studio():
    assert "agent" in CRAFT_MODES
    assert "agent" in MODE_TEMPERATURES
    prompt = CRAFT_MODES["agent"].lower()
    assert "agent studio" in prompt
    assert "tier" in prompt


def test_chat_endpoint_supports_agent_mode():
    token = register_user("agent_chat@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/chat",
        headers=headers,
        json={"message": "Inspect the codebase structure", "mode": "agent"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["mode_used"] == "agent"
    assert "Agent Studio" in data["response"]


def test_agent_studio_sse_stream_emits_typed_event_envelopes():
    token = register_user("agent_stream@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Analyze the repository architecture and plan next steps", "model": "llama3-8b-8192", "mode": "agent"},
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    events = parse_sse_blocks(res.text)
    thought_events = [e for e in events if e["event"] == "thought"]
    token_events = [e for e in events if e["event"] == "token"]
    done_events = [e for e in events if e["event"] == "done"]

    assert len(thought_events) >= 1
    assert isinstance(thought_events[0]["data"]["thought"], str)
    assert len(thought_events[0]["data"]["thought"].strip()) > 0

    assert len(token_events) >= 1
    assembled = "".join(e["data"]["token"] for e in token_events)
    assert "Agent" in assembled

    assert len(done_events) == 1
    done_data = done_events[0]["data"]
    assert done_data["status"] == "completed"
    assert done_data["totalSteps"] >= 1
    assert done_data["modeUsed"] == "agent"
    assert done_data["conversationId"] > 0
    assert done_data["tokensUsed"] > 0
    assert "tokensRemaining" in done_data
    assert done_data["modelUsed"] == "llama3-8b-8192"
    assert "conversation_id" not in done_data

    hist = client.get(f"/chat/{done_data['conversationId']}/history", headers=headers)
    assert hist.status_code == 200
    msgs = hist.json()
    assert len(msgs) == 2
    assert msgs[1]["content"] == assembled


def test_conversational_modes_preserve_legacy_sse_chunks():
    token = register_user("legacy_stream@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Explain REST vs GraphQL", "mode": "standard"},
    )
    assert res.status_code == 200
    events = parse_sse_blocks(res.text)

    assert all(e["event"] is None for e in events)
    assert any(e["data"].get("type") == "chunk" for e in events)
    done_events = [e for e in events if e["data"].get("type") == "done"]
    assert len(done_events) == 1
    assert done_events[0]["data"]["mode_used"] == "standard"


def test_agent_studio_stream_error_emits_typed_error_envelope():
    token = register_user("agent_err@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.services.chat.agent.stream") as mock_stream:
        mock_stream.side_effect = RuntimeError("Simulated Groq failure")
        res = client.post(
            "/chat/stream",
            headers=headers,
            json={"message": "Run diagnostics", "mode": "agent"},
        )

    assert res.status_code == 200
    events = parse_sse_blocks(res.text)
    error_events = [e for e in events if e["event"] == "error"]
    assert len(error_events) == 1
    assert "Simulated Groq failure" in error_events[0]["data"]["error"]


def test_workspace_root_resolution_and_path_safety():
    from app.ai.tools.workspace import get_workspace_root, resolve_workspace_path

    root = get_workspace_root()
    assert root.exists()
    assert (root / "backend").exists()

    # Relative to root
    resolved = resolve_workspace_path("README.md")
    assert resolved == (root / "README.md").resolve()

    # Directory traversal rejection
    with pytest.raises(ValueError) as exc:
        resolve_workspace_path("../../outside.txt")
    assert "Access denied" in str(exc.value)


def test_tier1_workspace_tools_execution_and_safety():
    from app.ai.tools.workspace import (
        read_workspace_file,
        list_workspace_directory,
        search_workspace_symbols,
        resolve_workspace_path,
        TIER_1_TOOLS,
        TOOL_TIERS,
        TOOL_CAPABILITY_TIERS,
        get_tool_tier,
    )

    assert len(TIER_1_TOOLS) == 3
    assert TOOL_TIERS["read_workspace_file"] == 1
    assert TOOL_CAPABILITY_TIERS["read_workspace_file"] == 1
    assert get_tool_tier("read_workspace_file") == 1
    assert get_tool_tier("list_workspace_directory") == 1
    assert get_tool_tier("search_workspace_symbols") == 1

    # Directory listing
    dir_listing = list_workspace_directory.invoke({"path": "."})
    entries = dir_listing.splitlines()
    assert "backend/" in entries
    assert ".git/" not in entries
    assert "node_modules/" not in entries

    # File reading
    content = read_workspace_file.invoke({"path": "README.md", "start_line": 1, "end_line": 5})
    assert "1:" in content
    assert len(content) > 0

    # Directory traversal safety via direct resolver
    with pytest.raises(ValueError) as exc:
        resolve_workspace_path("../../outside.txt")
    assert "Access denied" in str(exc.value)

    # Directory traversal safety via tool call
    traversal_result = read_workspace_file.invoke({"path": "../../../secret.txt"})
    assert "Error: Access denied" in traversal_result or "Access denied" in traversal_result

    # Symbol search
    search_result = search_workspace_symbols.invoke({"query": "ChatService", "path": "backend"})
    assert "backend/app/services/chat.py" in search_result or "services/chat.py" in search_result


def test_tier1_tool_output_truncation_to_4000_chars(tmp_path, monkeypatch):
    from app.ai.tools.workspace import (
        truncate_tool_output,
        MAX_TOOL_OUTPUT_CHARS,
        read_workspace_file,
    )

    short_text = "Hello world"
    assert truncate_tool_output(short_text) == short_text

    long_str = "x" * 6000
    truncated = truncate_tool_output(long_str)
    assert len(truncated) <= MAX_TOOL_OUTPUT_CHARS
    assert len(truncated) == MAX_TOOL_OUTPUT_CHARS
    assert "[Truncated to 4,000 chars]" in truncated

    # Test via read_workspace_file with temporary file in isolated tmp_path
    monkeypatch.setenv("GPTCRAFT_WORKSPACE_ROOT", str(tmp_path))
    test_file = tmp_path / "temp_truncation_test.txt"
    test_file.write_text("Long line of text for truncation testing.\n" * 200, encoding="utf-8")

    result = read_workspace_file.invoke({"path": "temp_truncation_test.txt", "start_line": 1, "end_line": 200})
    assert len(result) <= MAX_TOOL_OUTPUT_CHARS
    assert "[Truncated to 4,000 chars]" in result


def test_cyclical_react_loop_graph_execution():
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from app.ai.graph.agent import agent

    # Agent mode invokes Tier 1 tool, enters ToolNode, returns to chatbot, then ENDs
    state = {"messages": [HumanMessage(content="Inspect the workspace files")]}
    config = {"configurable": {"mode": "agent", "user_tier": "free", "model_id": "llama3-8b-8192"}}

    result = agent.invoke(state, config=config)
    messages = result["messages"]

    assert len(messages) >= 4
    assert isinstance(messages[0], HumanMessage)
    assert isinstance(messages[1], AIMessage)
    assert getattr(messages[1], "tool_calls", None) and len(messages[1].tool_calls) > 0
    assert messages[1].tool_calls[0]["name"] == "list_workspace_directory"

    assert isinstance(messages[2], ToolMessage)
    assert "backend/" in str(messages[2].content)

    assert isinstance(messages[3], AIMessage)
    assert not (getattr(messages[3], "tool_calls", None))
    assert "Agent Studio" in str(messages[3].content)

    # Conversational mode does not invoke tools
    std_state = {"messages": [HumanMessage(content="Explain quantum computing")]}
    std_config = {"configurable": {"mode": "standard", "user_tier": "free"}}
    std_result = agent.invoke(std_state, config=std_config)
    std_messages = std_result["messages"]
    assert len(std_messages) == 2
    assert isinstance(std_messages[1], AIMessage)
    assert not (getattr(std_messages[1], "tool_calls", None))


def test_agent_react_loop_emits_action_call_and_action_result_sse_envelopes():
    token = register_user("react_loop_stream@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Inspect the repository files and read GLOSSARY.md", "mode": "agent"},
    )
    assert res.status_code == 200
    events = parse_sse_blocks(res.text)

    event_names = [e["event"] for e in events]
    assert "thought" in event_names
    assert "action_call" in event_names
    assert "action_result" in event_names
    assert "token" in event_names
    assert "done" in event_names

    # Check action_call details
    action_calls = [e["data"] for e in events if e["event"] == "action_call"]
    assert len(action_calls) >= 1
    ac = action_calls[0]
    assert ac["tool"] == "read_workspace_file"
    assert ac["tier"] == 1
    assert "actionId" in ac
    assert ac["args"]["path"] == "GLOSSARY.md"

    # Check action_result details
    action_results = [e["data"] for e in events if e["event"] == "action_result"]
    assert len(action_results) >= 1
    ar = action_results[0]
    assert ar["actionId"] == ac["actionId"]
    assert ar["tool"] == "read_workspace_file"
    assert len(ar["output"]) > 0

    # Check token emission and final answer
    token_events = [e["data"] for e in events if e["event"] == "token"]
    assert len(token_events) >= 1
    assembled_answer = "".join(e["token"] for e in token_events)
    assert "Agent Studio" in assembled_answer or "GPTCraft" in assembled_answer

    # Check done envelope
    done_payload = [e["data"] for e in events if e["event"] == "done"][0]
    assert done_payload["totalSteps"] >= 2
    assert done_payload["status"] == "completed"
    assert done_payload["modeUsed"] == "agent"


def test_tier2_tool_triggers_interrupt_and_emits_approval_required(tmp_path, monkeypatch):
    monkeypatch.setenv("GPTCRAFT_WORKSPACE_ROOT", str(tmp_path))
    token = register_user("tier2_stream@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Please edit and update docs/test_edit.txt with new guidelines", "mode": "agent"},
    )
    assert res.status_code == 200
    events = parse_sse_blocks(res.text)
    event_names = [e["event"] for e in events]

    assert "thought" in event_names
    assert "action_call" in event_names
    assert "approval_required" in event_names
    assert "done" in event_names

    # Check action_call
    ac = [e["data"] for e in events if e["event"] == "action_call"][0]
    assert ac["tool"] == "edit_workspace_file"
    assert ac["tier"] == 2

    # Check approval_required
    appr = [e["data"] for e in events if e["event"] == "approval_required"][0]
    assert appr["actionId"].startswith("act_")
    assert appr["tool"] == "edit_workspace_file"
    assert appr["tier"] == 2
    assert "parameters" in appr
    assert "rationale" in appr
    assert "diff" in appr
    assert "+Updated content from Agent Studio" in appr["diff"]

    # Check done status is interrupted
    done_data = [e["data"] for e in events if e["event"] == "done"][0]
    assert done_data["status"] == "interrupted"
    assert done_data["actionId"] == appr["actionId"]


def test_chat_approval_endpoint_resumes_execution_on_approve(tmp_path, monkeypatch):
    monkeypatch.setenv("GPTCRAFT_WORKSPACE_ROOT", str(tmp_path))
    token = register_user("approval_approve@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Trigger interrupt
    res = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Create and write docs/test_edit.txt", "mode": "agent"},
    )
    events = parse_sse_blocks(res.text)
    appr = [e["data"] for e in events if e["event"] == "approval_required"][0]
    action_id = appr["actionId"]

    # Call POST /chat/approval with approve
    res_appr = client.post(
        "/chat/approval",
        headers=headers,
        json={"actionId": action_id, "decision": "approve"},
    )
    assert res_appr.status_code == 200
    resume_events = parse_sse_blocks(res_appr.text)
    resume_event_names = [e["event"] for e in resume_events]

    assert "action_result" in resume_event_names
    assert "token" in resume_event_names
    assert "done" in resume_event_names

    ar = [e["data"] for e in resume_events if e["event"] == "action_result"][0]
    assert ar["actionId"] == action_id
    assert "Successfully updated" in ar["output"]

    done_ev = [e["data"] for e in resume_events if e["event"] == "done"][0]
    assert done_ev["status"] == "completed"

    # Verify file actually created on disk
    target_file = tmp_path / "docs" / "test_edit.txt"
    assert target_file.exists()
    assert "Updated content from Agent Studio" in target_file.read_text(encoding="utf-8")


def test_chat_approval_endpoint_handles_modify_and_reject_with_feedback(tmp_path, monkeypatch):
    monkeypatch.setenv("GPTCRAFT_WORKSPACE_ROOT", str(tmp_path))
    token = register_user("approval_modify_reject@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Test Modify decision
    res = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Write docs/test_edit.txt with draft content", "mode": "agent"},
    )
    events = parse_sse_blocks(res.text)
    appr = [e["data"] for e in events if e["event"] == "approval_required"][0]
    action_id = appr["actionId"]

    res_modify = client.post(
        "/chat/approval",
        headers=headers,
        json={
            "actionId": action_id,
            "decision": "modify",
            "modifiedParams": {
                "path": "docs/custom_edit.txt",
                "content": "Customized user content after human review",
                "mode": "write",
            },
        },
    )
    assert res_modify.status_code == 200
    mod_events = parse_sse_blocks(res_modify.text)
    mod_done = [e["data"] for e in mod_events if e["event"] == "done"][0]
    assert mod_done["status"] == "completed"

    custom_file = tmp_path / "docs" / "custom_edit.txt"
    assert custom_file.exists()
    assert "Customized user content after human review" in custom_file.read_text(encoding="utf-8")

    # Test Reject decision with feedback
    res_rej_stream = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Edit docs/protected.txt", "mode": "agent"},
    )
    rej_events = parse_sse_blocks(res_rej_stream.text)
    rej_appr = [e["data"] for e in rej_events if e["event"] == "approval_required"][0]
    rej_action_id = rej_appr["actionId"]

    res_reject = client.post(
        "/chat/approval",
        headers=headers,
        json={
            "actionId": rej_action_id,
            "decision": "reject",
            "feedback": "Do not edit this protected file under any circumstances.",
        },
    )
    assert res_reject.status_code == 200
    reject_events = parse_sse_blocks(res_reject.text)
    reject_results = [e["data"] for e in reject_events if e["event"] == "action_result"]
    assert len(reject_results) >= 1
    assert "Action rejected by user" in reject_results[0]["output"]
    assert "Do not edit this protected file" in reject_results[0]["output"]

    # Verify protected file was NOT created
    protected_file = tmp_path / "docs" / "protected.txt"
    assert not protected_file.exists()

    # Verify agent re-planned
    token_events = [e["data"] for e in reject_events if e["event"] == "token"]
    full_text = "".join(t["token"] for t in token_events)
    assert "Re-planning" in full_text or "acknowledged" in full_text


def test_pending_approval_persists_and_restored(tmp_path, monkeypatch):
    monkeypatch.setenv("GPTCRAFT_WORKSPACE_ROOT", str(tmp_path))
    token = register_user("persists_approval@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Modify docs/persistent.txt", "mode": "agent"},
    )
    events = parse_sse_blocks(res.text)
    appr = [e["data"] for e in events if e["event"] == "approval_required"][0]
    conv_id = [e["data"] for e in events if e["event"] == "done"][0]["conversationId"]

    # Fetch pending approval for this conversation
    pending_res = client.get(f"/chat/{conv_id}/approval", headers=headers)
    assert pending_res.status_code == 200
    pending_data = pending_res.json()
    assert pending_data is not None
    assert pending_data["actionId"] == appr["actionId"]
    assert pending_data["tool"] == "edit_workspace_file"
    assert pending_data["status"] == "pending"
    assert "test_edit.txt" in str(pending_data["parameters"]) or "persistent.txt" in str(pending_data["parameters"])

    # Resolve approval
    client.post(
        "/chat/approval",
        headers=headers,
        json={"actionId": appr["actionId"], "decision": "approve"},
    )

    # Check that pending approval is now None
    after_res = client.get(f"/chat/{conv_id}/approval", headers=headers)
    assert after_res.status_code == 200
    assert after_res.json() is None


def test_run_terminal_command_registration_and_tier():
    from app.ai.tools.workspace import (
        run_terminal_command,
        TIER_2_TOOLS,
        TOOL_TIERS,
        TOOL_CAPABILITY_TIERS,
        get_tool_tier,
    )

    assert run_terminal_command in TIER_2_TOOLS
    assert TOOL_TIERS["run_terminal_command"] == 2
    assert TOOL_CAPABILITY_TIERS["run_terminal_command"] == 2
    assert get_tool_tier("run_terminal_command") == 2


def test_run_terminal_command_successful_execution():
    import sys
    from app.ai.tools.workspace import run_terminal_command

    cmd = f'"{sys.executable}" -c "print(\'Hello GPTCraft\')"'
    res = run_terminal_command.invoke({"command": cmd})

    assert "Exit code: 0" in res
    assert "Hello GPTCraft" in res


def test_run_terminal_command_timeout_enforcement():
    import sys
    from app.ai.tools.workspace import run_terminal_command

    # Explicit timeout parameter
    sleep_cmd = f'"{sys.executable}" -c "import time; time.sleep(5)"'
    res = run_terminal_command.invoke({"command": sleep_cmd, "timeout": 1})
    assert "Error: Command timed out after 1 seconds." in res


def test_run_terminal_command_timeout_via_env_var(monkeypatch):
    import sys
    from app.ai.tools.workspace import run_terminal_command

    monkeypatch.setenv("GPTCRAFT_COMMAND_TIMEOUT", "1")
    sleep_cmd = f'"{sys.executable}" -c "import time; time.sleep(5)"'
    res = run_terminal_command.invoke({"command": sleep_cmd})
    assert "Error: Command timed out after 1 seconds." in res


def test_run_terminal_command_non_interactive_stdin_behavior():
    import sys
    from app.ai.tools.workspace import run_terminal_command

    # Non-interactive stdin: commands attempting to read stdin fail or exit without hanging
    stdin_cmd = f'"{sys.executable}" -c "input(\'Enter something: \')"'
    res = run_terminal_command.invoke({"command": stdin_cmd})
    assert "Exit code:" in res
    # With stdin=subprocess.DEVNULL, python input() raises EOFError and returns non-zero
    assert "EOFError" in res or "Exit code: 1" in res or "Exit code: 0" not in res

    # Block interactive editor/pager commands
    res_nano = run_terminal_command.invoke({"command": "nano docs/readme.txt"})
    assert "Error: Command aborted. Interactive command detected" in res_nano
    assert "interactive text editor" in res_nano

    res_vim = run_terminal_command.invoke({"command": "vim app/main.py"})
    assert "Error: Command aborted. Interactive command detected" in res_vim

    res_git = run_terminal_command.invoke({"command": "git rebase -i HEAD~3"})
    assert "Error: Command aborted. Interactive command detected" in res_git
    assert "interactive git rebase" in res_git


def test_run_terminal_command_path_jail_violation():
    from app.ai.tools.workspace import run_terminal_command

    # Traversal escaping workspace root
    res_escape = run_terminal_command.invoke({"command": "cat ../../outside.txt"})
    assert "Error: Access denied" in res_escape
    assert "escapes workspace root" in res_escape


def test_run_terminal_command_hitl_mock_lifecycle():
    import sys
    from unittest.mock import patch
    from app.ai.tools.workspace import run_terminal_command

    # 1. Approval flow
    with patch("app.ai.tools.workspace.interrupt") as mock_interrupt:
        mock_interrupt.return_value = {"decision": "approve"}
        res_approve = run_terminal_command.invoke({
            "command": f'"{sys.executable}" -c "print(\'Approved execution\')"',
            "rationale": "Verifying test suite",
        })
        assert "Exit code: 0" in res_approve
        assert "Approved execution" in res_approve

    # 2. Rejection flow with user feedback
    with patch("app.ai.tools.workspace.interrupt") as mock_interrupt:
        mock_interrupt.return_value = {
            "decision": "reject",
            "feedback": "Commands are restricted in read-only audit mode.",
        }
        res_reject = run_terminal_command.invoke({
            "command": "pytest backend/tests",
            "rationale": "Running test suite",
        })
        assert "Action rejected by user. Feedback: Commands are restricted in read-only audit mode." in res_reject

    # 3. Modification flow
    with patch("app.ai.tools.workspace.interrupt") as mock_interrupt:
        mock_interrupt.return_value = {
            "decision": "modify",
            "modifiedParams": {
                "command": f'"{sys.executable}" -c "print(\'Overridden command\')"'
            },
        }
        res_mod = run_terminal_command.invoke({
            "command": "original dangerous command",
            "rationale": "Running test suite",
        })
        assert "Exit code: 0" in res_mod
        assert "Overridden command" in res_mod


def test_run_terminal_command_chat_stream_approval_and_resumption():
    import sys
    token = register_user("terminal_approval@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Request terminal command execution in Agent Studio mode
    res = client.post(
        "/chat/stream",
        headers=headers,
        json={"message": "Run terminal command pytest tests/test_api.py", "mode": "agent"},
    )
    assert res.status_code == 200
    events = parse_sse_blocks(res.text)
    event_names = [e["event"] for e in events]

    assert "thought" in event_names
    assert "action_call" in event_names
    assert "approval_required" in event_names
    assert "done" in event_names

    ac = [e["data"] for e in events if e["event"] == "action_call"][0]
    assert ac["tool"] == "run_terminal_command"
    assert ac["tier"] == 2

    appr = [e["data"] for e in events if e["event"] == "approval_required"][0]
    assert appr["actionId"].startswith("act_")
    assert appr["tool"] == "run_terminal_command"
    assert appr["tier"] == 2
    assert "command" in appr["parameters"]

    action_id = appr["actionId"]

    # Step 2: Resume via POST /chat/approval with modify decision
    modified_cmd = f'"{sys.executable}" -c "print(\'Modified command executed successfully\')"'
    res_appr = client.post(
        "/chat/approval",
        headers=headers,
        json={
            "actionId": action_id,
            "decision": "modify",
            "modifiedParams": {"command": modified_cmd},
        },
    )
    assert res_appr.status_code == 200
    resume_events = parse_sse_blocks(res_appr.text)
    resume_names = [e["event"] for e in resume_events]

    assert "action_result" in resume_names
    assert "token" in resume_names
    assert "done" in resume_names

    ar = [e["data"] for e in resume_events if e["event"] == "action_result"][0]
    assert ar["actionId"] == action_id
    assert ar["tool"] == "run_terminal_command"
    assert "Modified command executed successfully" in ar["output"]
    assert "Exit code: 0" in ar["output"]

    done_ev = [e["data"] for e in resume_events if e["event"] == "done"][0]
    assert done_ev["status"] == "completed"





