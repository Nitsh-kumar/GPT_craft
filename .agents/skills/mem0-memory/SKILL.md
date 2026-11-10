---
name: mem0-memory
description: >-
  Manage and access long-term persistent agent and user memory using Mem0.
  Use this skill whenever you need to search previous context or preferences,
  persist important architectural decisions, track project guidelines, store runbook solutions,
  or manage the user's persistent memory store.
---

# Mem0 Long-Term Memory Skill

## Overview

This skill equips the agent with persistent, long-term memory powered by **Mem0**.
Credentials and default scopes are managed locally in `~/.mem0/config.json` (Platform SaaS endpoint `https://api.mem0.ai` with user scope `nit2314`).

Use Mem0 to:
1. **Retrieve user preferences and past project decisions** before implementing complex features.
2. **Persist important facts, conventions, and solutions** that should survive across conversation sessions.
3. **Keep an audit trail of architectural milestones and user requirements**.

---

## 1. Checking Memory Status & Connectivity

```powershell
mem0 status
```
Outputs the active backend (`platform`), connection status, API URL (`https://api.mem0.ai`), and latency.

---

## 2. Searching Memories (Semantic & Keyword Retrieval)

Search across user memories before starting major tasks:

```powershell
# Semantic search with JSON output
mem0 --json search "<natural language query>"

# Example: search for project preferences or auth rules
mem0 --json search "FastAPI React architecture conventions"
```

The output returns matching memories with relevance `score`, `id`, `created_at`, and `categories`.

---

## 3. Adding New Memories

Persist key facts, user preferences, and permanent architectural decisions:

```powershell
# Add a memory fact (scoped to active user by default)
mem0 --json add "<concise factual statement>"

# Example:
mem0 --json add "User prefers camelCase for all JSON API keys and snake_case for Python backend internals"

# Adding with specific category:
mem0 --json add "Backend verification script is scripts/verify.ps1" --categories "devops,testing"
```

*Note: Mem0 processes memory additions asynchronously. An `event_id` is returned with status `PENDING`, and memories are typically indexed within a second.*

---

## 4. Listing and Filtering Memories

```powershell
# List recent memories
mem0 --json list

# Filter by category
mem0 --json list --category "technology"
```

---

## 5. Updating or Deleting Memories

```powershell
# Update an existing memory
mem0 update <memory_id> "<updated fact or context>"

# Delete an obsolete memory
mem0 delete <memory_id> --yes
```

---

## 6. Helper Script

The harness provides a bundled PowerShell helper:

```powershell
powershell -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action search -QueryOrText "FastAPI" -Json
powershell -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action add -QueryOrText "New preference"
powershell -ExecutionPolicy Bypass -File .agents/scripts/mem0_helper.ps1 -Action list
```

---

## Best Practices for Agent Memory Management

1. **Be Concise & Declarative**: Store facts as standalone truths (e.g. *"Frontend uses Tailwind v4 with @tailwindcss/vite; do not use tailwind.config.js"*).
2. **Avoid Temporary State**: Do not store transient variables or ephemeral bugs; store durable patterns, preferences, and verified decisions.
3. **Session Warmup**: On `SessionStart`, active memories are automatically surfaced in the session prompt via `.agents/scripts/session_start.ps1`.
