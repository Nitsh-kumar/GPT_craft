# Personal Agent Execution Boundaries & Safety Tiers

## Context
GPTCraft is evolving from a passive conversational workbench into an autonomous Personal Agent capable of executing workspace actions and technical research. Without well-defined execution boundaries, personal agents suffer from context window saturation (Open Interpreter), non-deterministic loops (AutoGPT), or destructive command execution.

## Decision
1. **Scope**: Focus Day 1 on Developer Workspace Automation (file inspection/editing, test and lint execution via terminal, git inspection) and live technical web research.
2. **Runtime**: Execute tools directly on the host workspace directory, bounded by path restrictions (no container prerequisite for local developer workflows).
3. **Safety Tiers**:
   - **Tier 1 (Read-Only / Search)**: Auto-executed without user interruption (reading files, directory listing, web research).
   - **Tier 2 (Workspace Mutations)**: 1-click confirmation required (editing files, running build/tests, creating branches).
   - **Tier 3 (External / Destructive)**: Explicit command inspection and diff review required (deleting files, running package installs, external network mutations).
4. **Command Constraints**: Strictly non-interactive execution (fails immediately if stdin prompt is requested), 30-second default timeout, and strict working-directory confinement to the project root.
5. **Streaming Protocol**: Structured SSE envelopes (`thought`, `action_call`, `approval_required`, `action_result`, `token`, `done`).
6. **UI Mode**: Add a dedicated `Agent Studio` mode in the React 19 frontend with real-time action telemetry and approval cards.
