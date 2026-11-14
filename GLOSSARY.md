# GPTCraft Glossary

GPTCraft is an **operator-hosted multi-tenant Personal Agent SaaS** providing isolated per-user agent execution, live action visibility, Human-in-the-Loop (HITL) approval before sensitive mutations, persistent cross-session memory, and plan-gated token quotas.

## Domain Language

### Identity, Tenancy & Subscription

**User**:
An authenticated individual with an assigned `Plan`, active status, and strictly isolated tenant data.
_Avoid_: Account, member, client

**Tenant Isolation**:
The strict per-user boundary enforced via `user_id` ownership checks and PostgreSQL Row-Level Security (RLS) across conversations, messages, memories, approvals, and checkpoints, preventing cross-tenant access or model training on tenant data.
_Avoid_: Shared workspace, global memory

**Plan**:
A subscription entitlement dictating daily request/token quotas and unlocked models.
_Avoid_: Pricing level, package, subscription tier

**Plan Type**:
One of the three canonical service tiers: `free`, `super`, or `hyper` (legacy `pro` maps to paid equivalent; public plan mutation is disabled pending verified billing).
_Avoid_: Pro, tier level, subscription tier

**Quota**:
The remaining and total daily UTC allowance of tokens and requests allocated per user (`DailyQuota`, `QuotaReservation`).
_Avoid_: Rate limit bucket, budget, balance

**Token Usage**:
The discrete prompt and completion token count settled for an assistant turn (`tokens_used`, with `usage_estimated` flagged when provider usage is unavailable).
_Avoid_: Token cost, spend, consumption tally

---

### Personal Agent & Execution

**Agent Studio**:
The primary personal-agent workbench surface (`mode: "agent"` in v1 compatibility routes) pairing live reasoning and tool telemetry (`TelemetryDrawer`) with interactive HITL confirmation (`ApprovalCard`).
_Avoid_: Agent tab, copilot view, bot screen

**Action**:
A discrete tool invocation emitted by the agent (`action_call` / `action_result`), governed by a `Capability Tier`.
_Avoid_: Function run, tool command, execution step

**Capability Tier**:
Safety classification governing agent tool execution:
- `Tier 1 (Read-Only)`: Auto-executed without interruption (`read_workspace_file`, `list_workspace_directory`, `search_workspace_symbols`, output truncated to 4,000 characters).
- `Tier 2 (Workspace Mutation)`: Pauses via `HITL Interruption` (`edit_workspace_file`, `run_terminal_command`, and default tier for MCP-federated tools).
- `Tier 3 (Destructive / External)`: Reserved safety tier requiring explicit command and diff inspection (no built-in Tier 3 tools are implemented yet).
_Avoid_: Risk level, permission grade, privilege tier

**Sandbox Boundary**:
The execution containment boundary around agent tools and external MCP connectors. Host workspace tools (`backend/app/ai/tools/workspace.py`) and host `stdio` MCP servers (`backend/app/ai/mcp/manager.py`) are dev/single-operator gated until per-user isolated sandboxes exist.
_Avoid_: Host shell access, unrestricted runner

**HITL Interruption**:
A suspended LangGraph execution (`interrupt()`) persisted via `SQLAlchemyCheckpointSaver` (`agent_checkpoints`, `agent_checkpoint_blobs`, `agent_checkpoint_writes`) and `AgentApproval`, awaiting an `Action Decision` through `POST /chat/approval`.
_Avoid_: Pause, blocking prompt, user gate

**Approval Card**:
The interactive UI component (`ApprovalCard`) presenting a pending action's tool name, capability tier, rationale, target path or command, unified diff / command preview, and resolution controls.
_Avoid_: Confirmation modal, approval popup, permission prompt

**Action Decision**:
One of the three human resolution states for an interrupted action: `approve`, `modify`, or `reject`.
_Avoid_: User choice, action verdict

**Telemetry Drawer**:
The collapsible per-turn inspector (`TelemetryDrawer`) displaying model reasoning traces, tool call inputs, capability tier badges, stdout/stderr outputs, and execution latency.
_Avoid_: Debug console, raw log dump

**Event Envelope**:
A typed Server-Sent Events (SSE) payload (`thought`, `action_call`, `approval_required`, `action_result`, `token`, `done`, `error`) separating agent telemetry and HITL interrupts from assistant response tokens.
_Avoid_: Message packet, event chunk

**Model**:
A specific underlying LLM identifier exposed by the catalog (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`), gated by `Plan Type`.
_Avoid_: Engine, LLM version, provider endpoint

---

### Memory & Personalization

**User Preferences**:
Per-user personalization settings storing profile context, response style instructions, and the memory toggle (`UserPreferences`, served at `/memory/preferences`).
_Avoid_: System bio, prompt settings

**Episodic Memory**:
A persistent user-scoped fact (`UserMemory` in categories `general`, `tech_stack`, `project`, `preference`) extracted via SQL + deterministic regex heuristics (`backend/app/services/memory.py`) or added manually via `/memory`. Distinct from Mem0, which is strictly for the `.agents/` developer harness.
_Avoid_: Global knowledge, developer Mem0 store

**Personalization Modal**:
The two-tab UI dialog (`PersonalizationModal`) for editing `Custom Instructions` and managing `Remembered Facts`.
_Avoid_: Profile settings popup, memory drawer

---

### Conversation & v1 Compatibility Identifiers

**Conversation**:
An ordered sequence of messages and agent checkpoints owned by a single user.
_Avoid_: Chat, chat session, thread, dialog

**Message**:
A single turn within a conversation attributed to a `Role` (`user`, `assistant`, or `system`).
_Avoid_: Bubble, turn, prompt, entry

**Role**:
The sender category of a message (`user`, `assistant`, or `system`).
_Avoid_: Author type, sender kind

**v1 Compatibility Identifiers (`CraftMode`, `/chat`)**:
Legacy conversational persona modes (`standard`, `architect`, `code`, `brainstorm`, `agent`) and `/chat` API/UI route paths retained for v1 backward compatibility while GPTCraft transitions to the Personal Agent SaaS domain model.
_Avoid_: Treating `CraftMode` or `/chat` as the long-term product identity.
