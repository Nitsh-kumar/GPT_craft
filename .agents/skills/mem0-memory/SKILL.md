---
name: mem0-memory
description: >-
  Manage and access optional developer preference memory for the GPTCraft
  Personal Agent harness using Mem0. Use this skill only when explicitly storing
  or retrieving personal developer preferences across coding sessions via
  .agents/scripts/mem0_helper.ps1.
---

# Mem0 Developer Preference Memory Skill

## Scope & Source-of-Truth Boundaries

This skill covers **developer preference memory only** for the `.agents/` coding harness, backed by the Mem0 CLI (`~/.mem0/config.json`, never committed to git) and `.agents/scripts/mem0_helper.ps1`.

- **Developer Preferences Only**: Store only personal developer preferences and session notes (e.g., preferred shell or review style) scoped to `$env:MEM0_USER_ID` (or explicit `-UserId <user-id>`).
- **Never Runtime Agent Memory**: GPTCraft's runtime user personalization and episodic memories live in SQLAlchemy (`UserPreferences` and `UserMemory` in `backend/app/db/models.py`) and `backend/app/services/memory.py`, exposed via `backend/app/api/routes/memory.py` (`/memory`). Mem0 is never used by the application runtime.
- **Never Architecture Ground Truth**: Committed repository documents (`AGENTS.md`, `docs/OPERATIONS.md`, `docs/PROJECT_STATUS.md`, and `docs/adr/`) are the canonical source of architectural decisions and system state. Never treat Mem0 notes as authoritative over code or committed docs.
- **Offline `SessionStart` Hook**: `.agents/scripts/session_start.ps1` runs completely offline and does **not** query or surface memories automatically on startup. Load or record developer preferences deliberately via `.agents/scripts/mem0_helper.ps1`.

---

## Supported Helper Actions

`.agents/scripts/mem0_helper.ps1` supports `ValidateSet("status", "list", "search", "add", "get", "delete", "help")`.

Set `$env:MEM0_USER_ID` (or pass `-UserId <user-id>`) for user-scoped actions (`list`, `search`, `add`):

```powershell
$env:MEM0_USER_ID = "<user-id>"
```

### 1. Check Connectivity (`status`)

```powershell
pwsh -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action status
pwsh -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action status -Json
```

### 2. List Memories (`list`)

Requires `$env:MEM0_USER_ID` or `-UserId`:

```powershell
pwsh -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action list -Json
pwsh -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action list -UserId "<user-id>"
```

### 3. Search Memories (`search`)

Requires `-QueryOrText` and `$env:MEM0_USER_ID` (or `-UserId`):

```powershell
pwsh -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action search -QueryOrText "shell preference" -Json
```

### 4. Add a Developer Preference (`add`)

Requires `-QueryOrText` and `$env:MEM0_USER_ID` (or `-UserId`):

```powershell
pwsh -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action add -QueryOrText "Prefer concise diff summaries in review notes" -Json
```

### 5. Get or Delete by ID (`get`, `delete`)

Requires `-Id` (`delete` passes `--force` to `mem0 delete`; to revise a stale fact, delete the obsolete entry and add a replacement):

```powershell
pwsh -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action get -Id "<memory_id>" -Json
pwsh -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action delete -Id "<memory_id>"
```

### 6. Help (`help`)

```powershell
pwsh -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action help
```

---

## Best Practices

1. **Keep Entries Scoped to Developer Preferences**: Do not store credentials, tokens, PII, or transient debugging artifacts.
2. **Verify Against Repository Files**: Before acting on any retrieved Mem0 note about project behavior, verify it against committed code and docs (`AGENTS.md`, `docs/OPERATIONS.md`, `docs/adr/`).
3. **Treat Missing Configuration as No-Op**: If `MEM0_USER_ID` or Mem0 CLI credentials are absent, proceed cleanly without Mem0 rather than guessing or hardcoding user IDs.
