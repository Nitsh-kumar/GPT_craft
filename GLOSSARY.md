# GPTCraft

GPTCraft is an AI conversational platform providing tiered access to diverse LLM inference modes with persistent history and quota tracking.

## Language

### Identity & Subscription

**User**:
An authenticated individual with an assigned plan and owned conversations.
_Avoid_: Account, member, client

**Plan**:
A subscription level that dictates token quotas, available models, and craft modes.
_Avoid_: Pricing level, package, subscription tier

**Plan Type**:
One of the three canonical service levels: `free`, `super`, or `hyper`.
_Avoid_: Pro, tier level, subscription tier

### Conversation & Messaging

**Conversation**:
An ordered sequence of messages belonging to a single user.
_Avoid_: Chat, chat session, thread, dialog

**Message**:
A single turn within a conversation attributed to a role (`user`, `assistant`, or `system`).
_Avoid_: Bubble, turn, prompt, entry

**Role**:
The sender category of a message, determining whether it represents human input, model generation, or context steering.
_Avoid_: Author type, sender kind

### AI & Inference

**Craft Mode**:
A persona and prompt-steering configuration that shapes how the assistant reasons and formats its response (`standard`, `architect`, `code`, or `brainstorm`).
_Avoid_: Agent persona, chat style, system mode, flavor

**Model**:
A specific underlying large language model available for generation, gated by plan type.
_Avoid_: Engine, LLM version, provider endpoint

### Accounting & Quota

**Quota**:
The remaining and total allowance of token consumption and requests allocated to a user per period.
_Avoid_: Rate limit, token bucket, budget, balance

**Token Usage**:
The discrete count of prompt and completion tokens incurred during an assistant reply.
_Avoid_: Token cost, spend, consumption tally
