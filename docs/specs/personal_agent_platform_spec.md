## Problem Statement

Users of GPTCraft currently interact with a passive conversational AI assistant. While it generates high-quality text and code suggestions, it cannot interact with the user's local workspace, run automated test suites, inspect files, or execute tools on their behalf. Users are forced to manually copy code between the browser and their IDE, run terminal commands themselves, paste error messages back into the chat, and repeat instructions across sessions. Existing external personal agents (such as Open Interpreter or AutoGPT) either suffer from unsafe terminal execution and prompt context explosion or fall into non-deterministic planning loops without human-in-the-loop safety controls.

## Solution

Transform GPTCraft into a stateful, autonomous Personal Agent platform by introducing a dedicated **Agent Studio** craft mode. The platform combines a cyclical **LangGraph ReAct loop** with **Model Context Protocol (MCP)** tool federation, **Mem0** episodic long-term memory, and a strict **3-Tier Human-in-the-Loop (HITL)** safety model. Users can task the agent with developer workspace automation and live technical web research. Read-only actions execute automatically, while workspace mutations and destructive actions pause at durable database checkpoints, presenting structured **Approval Cards** with syntax-highlighted diffs in the studio workbench where users can approve, edit, or reject the planned action before resumption.

## User Stories

1. As a developer, I want to switch to the **Agent Studio** mode, so that I can delegate multi-step workspace tasks to an autonomous agent rather than copy-pasting code manually.
2. As a user, I want to submit high-level goals (e.g., "Inspect the repository and run all tests"), so that the agent formulates an autonomous plan and executes the necessary tools.
3. As a developer, I want the agent to auto-execute **Tier 1 (Read-Only / Search)** actions (such as reading files, listing directories, and searching documentation) without interrupting me, so that research and analysis remain fast and fluid.
4. As a developer, I want the agent to pause and request confirmation for **Tier 2 (Workspace Mutation)** actions (such as editing files, creating branches, or running tests), so that my workspace is never modified without my explicit consent.
5. As a developer, I want the agent to require detailed review and diff inspection for **Tier 3 (Destructive / External)** actions (such as deleting files or installing packages), so that dangerous commands are prevented.
6. As a user, I want to see an interactive **Approval Card** with the agent's rationale, exact tool parameters, and syntax-highlighted code diff, so that I can evaluate the planned change before it runs.
7. As a developer, I want to click **Approve & Run** on an Approval Card, so that the agent immediately executes the proposed action and continues its reasoning cycle.
8. As a developer, I want to click **Modify & Run** to adjust proposed code diffs or command flags before dispatching, so that I can correct minor mistakes without aborting the entire turn.
9. As a developer, I want to click **Reject with Feedback** to cancel an action and supply an explanation, so that the agent can acknowledge the cancellation and adapt its strategy.
10. As a user, I want real-time **SSE Event Envelopes** (`thought`, `action_call`, `approval_required`, `action_result`, `token`, `done`), so that internal reasoning and tool telemetry are visually separated from conversational prose.
11. As a user, I want a collapsible **Telemetry Drawer** beneath each turn, so that I can inspect tool inputs, stdout/stderr outputs, and execution latency without cluttering my reading experience.
12. As a power user, I want the agent to connect to external tools via the **Model Context Protocol (MCP)** (`stdio` and `sse` transports), so that I can plug in Git, filesystem, SQLite, and Brave Search servers dynamically.
13. As a developer, I want tool executions to enforce a **30-second timeout** and **non-interactive guardrails**, so that rogue processes or commands prompting for stdin do not hang the server.
14. As a user, I want filesystem and command execution to be **jailed to the active project root**, so that the agent cannot read or alter files outside the project directory.
15. As a user, I want the agent to recall my coding preferences, tech stack choices, and past fixes via **Mem0 episodic memory**, so that I do not need to re-explain my environment in every session.
16. As a user, I want long tool outputs to be **automatically truncated** to token safety budgets, so that intermediate execution logs do not saturate the LLM's context window.
17. As a user, I want my pending approval requests to **survive browser refreshes and session restarts**, so that I can resume a paused agent action after closing my laptop.
18. As an administrator, I want tool execution and agent reasoning to be **metered against user plan quotas** (Free, Super, Hyper), so that resource consumption is fairly regulated.
19. As a developer, I want to halt an active agent loop at any time with a **Stop** button, so that runaway reasoning cycles can be terminated instantly.

## Implementation Decisions

### Modules to Build & Modify
- **LangGraph Agent Engine**: Upgrade the single-node chatbot graph into a cyclic ReAct state machine using `ToolNode` and `tools_condition` from `langgraph.prebuilt`.
- **HITL Interruption Layer**: Implement state suspension using LangGraph's native `interrupt()` primitive, backed by database checkpointing (SQLite in local dev, PostgreSQL in production).
- **MCP Client Manager**: Create an extensible MCP manager in the backend that spawns and communicates with MCP servers via `stdio` and `sse` transports, dynamically translating MCP tools into LangChain `StructuredTool` instances.
- **FastAPI Transport Routes**: Extend `POST /chat/stream` with typed SSE event envelopes and introduce `POST /chat/approval` for resuming paused checkpoints with approval decisions.
- **React 19 Workbench**: Update the studio UI to support `Agent Studio` mode, rendering inline/collapsible action telemetry badges and interactive **Approval Cards** with diff viewers.

### Prototype Decisions Inlined
From prototype spike (branch `prototype/langgraph-react-loop`):
- The cyclical graph structure uses conditional edges:
  `graph_builder.add_conditional_edges("chatbot", tools_condition)`
  `graph_builder.add_edge("tools", "chatbot")`
- Typed event envelope stream format:
  `event: thought` $\rightarrow$ `{"thought": str}`
  `event: action_call` $\rightarrow$ `{"actionId": str, "tool": str, "args": dict, "tier": int}`
  `event: approval_required` $\rightarrow$ `{"actionId": str, "tool": str, "tier": int, "parameters": dict, "rationale": str}`
  `event: action_result` $\rightarrow$ `{"actionId": str, "tool": str, "output": str}`
  `event: token` $\rightarrow$ `{"token": str}`
  `event: done` $\rightarrow$ `{"status": str, "totalSteps": int}`

From UI prototype (branch `prototype/agent-action-cockpit`):
- Approval Cards render inline within the message flow with a dedicated diff container and three action triggers: `Approve & Run`, `Modify Diff`, and `Reject`.

## Testing Decisions

### Testing Philosophy
Only test external observable behavior at the highest available seam, never internal graph node transitions or private state keys.

### Seams & Prior Art
1. **Primary Backend Seam (HTTP / SSE Integration)**:
   - Tool: `fastapi.testclient.TestClient`
   - Endpoint: `POST /chat/stream` & `POST /chat/approval`
   - Behavior verified: Simulating multi-turn agent goals, verifying that Tier 1 actions auto-execute and emit `action_result` events, Tier 2 actions suspend execution and emit `approval_required` events, and calling `POST /chat/approval` resumes execution and yields the final `token` stream.
   - Prior Art: `tests/test_api.py::test_sse_stream_endpoint_and_quota_exhaustion` and `tests/test_memory.py::test_streaming_sse_endpoint`.
2. **Frontend Playwright E2E Seam**:
   - Tool: Playwright browser test runner
   - Behavior verified: Switching to Agent mode, triggering an action, verifying that the Approval Card renders with diff preview, clicking Approve, and confirming that output logs and the final assistant response are displayed.
   - Prior Art: `frontend/e2e/app.spec.ts`.
3. **Execution Guardrails Seam**:
   - Pytest unit tests verifying that terminal execution commands exceeding 30 seconds are timed out, commands requesting stdin abort immediately, and path jail violations outside the workspace root are blocked.

## Out of Scope

- Direct operating system pixel-level computer vision clicking (OSWorld-style screenshot automation).
- Native mobile client development (iOS/Android).
- Self-hosted raw LLM weights / local PyTorch GPU serving (Groq LPU API + Ollama MCP is preferred).
- Third-party personal cloud OAuth integrations (Google Calendar, Gmail, Slack API) during Phase 1.

## Further Notes

- Respects all canonical definitions in `GLOSSARY.md` (`Agent Studio`, `Action`, `Capability Tier`, `HITL Interruption`, `Approval Card`, `Action Decision`, `Event Envelope`).
- Complies with `docs/adr/0001-canonical-plan-hierarchy.md`, `docs/adr/0002-personal-agent-execution-boundaries.md`, and `docs/adr/0003-hitl-interruption-and-approval-protocol.md`.
