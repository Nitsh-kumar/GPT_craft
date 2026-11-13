"""Async graph: native model chunks propagate through stream_mode='messages' with HITL tools."""
import asyncio
import uuid
from typing import List, Optional
import httpx
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from app.ai.graph.checkpointer import SQLAlchemyCheckpointSaver
from app.ai.graph.state import AgentState
from app.ai.llm import get_llm, CRAFT_MODES
from app.ai.mcp import mcp_manager
from app.ai.tools.workspace import TIER_1_TOOLS, TIER_2_TOOLS
from app.core.config import get_settings

# Define static built-in tools (Tier 1 read-only + Tier 2 HITL file & terminal mutation tools)
tools = list(TIER_1_TOOLS) + list(TIER_2_TOOLS)


def get_agent_tools():
    """Return built-in workspace tools combined with any healthy MCP tools."""
    try:
        mcp_tools = mcp_manager.get_tools()
    except Exception:
        mcp_tools = []
    seen = {t.name for t in tools}
    return tools + [t for t in mcp_tools if t.name not in seen]

# Maximum messages kept in the sliding context window (plus system prompt)
MAX_CONTEXT_MESSAGES = 10


def build_personalization_block(
    user_instructions: Optional[str],
    relevant_memories: Optional[List[str]],
) -> str:
    """
    Formats user instructions and retrieved memories from AgentState into a
    markdown personalization section for the system prompt.
    """
    has_instructions = bool(user_instructions and user_instructions.strip())
    has_memories = bool(relevant_memories)
    if not (has_instructions or has_memories):
        return ""

    parts = ["\n\n---\n## User Personalization & Persistent Context"]
    if has_instructions:
        parts.append(user_instructions.strip())
    if has_memories:
        memory_lines = "\n".join(f"- {m}" for m in relevant_memories)
        parts.append(f"### Relevant Long-Term Memories:\n{memory_lines}")

    parts.append(
        "### Behavioral Personalization Rules:\n"
        "- Tailor answers, tone, tech stack choices, and code structure to these preferences.\n"
        "- Do not explicitly state 'According to your memory...' or 'Since you told me...'; "
        "naturally apply this context as an intelligent partner."
    )
    return "\n\n".join(parts)


async def chatbot_node(state: AgentState, config: RunnableConfig):
    """
    Async reasoning node:
    - Merges Craft Mode master prompts with active user personalization & memory context.
    - Applies a sliding message window to optimize token budget.
    - Binds workspace tools in 'agent' mode and honors cancellation events.
    """
    options = config.get("configurable", {})
    user_tier = options.get("user_tier", "free")
    model_id = options.get("model_id")
    mode = (options.get("mode") or "standard").lower()

    base_system_prompt = CRAFT_MODES.get(mode, CRAFT_MODES["standard"])
    personalization_block = build_personalization_block(
        state.get("user_instructions"),
        state.get("relevant_memories"),
    )
    full_system_prompt = base_system_prompt + personalization_block

    raw_messages = list(state.get("messages", []))
    trimmed_messages = (
        raw_messages[-MAX_CONTEXT_MESSAGES:]
        if len(raw_messages) > MAX_CONTEXT_MESSAGES
        else raw_messages
    )
    messages = [SystemMessage(content=full_system_prompt)] + trimmed_messages

    timeout_seconds = get_settings().generation_timeout_seconds
    cancel_event = options.get("cancel_event")

    # Request-scoped transport closes sockets even when the graph is cancelled.
    async with httpx.AsyncClient(timeout=timeout_seconds) as transport:
        llm = get_llm(
            tier=user_tier,
            model_id=model_id,
            mode=mode,
            http_async_client=transport,
        )
        active_tools = get_agent_tools() if mode == "agent" else []
        llm_with_tools = llm.bind_tools(active_tools) if active_tools else llm

        if cancel_event is None:
            response = await llm_with_tools.ainvoke(messages, config=config)
            return {"messages": [response]}

        generation = asyncio.create_task(llm_with_tools.ainvoke(messages, config=config))
        cancelled = asyncio.create_task(cancel_event.wait())
        try:
            done, _ = await asyncio.wait(
                [generation, cancelled],
                timeout=timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if cancelled in done:
                raise asyncio.CancelledError
            if generation not in done:
                raise TimeoutError("Generation deadline exceeded")
            response = generation.result()
        finally:
            generation.cancel()
            cancelled.cancel()
            await asyncio.gather(generation, cancelled, return_exceptions=True)

    return {"messages": [response]}


async def tools_node(state: AgentState, config: RunnableConfig):
    """Execute built-in workspace tools alongside active MCP server tools."""
    return await ToolNode(get_agent_tools()).ainvoke(state, config=config)


graph_builder = StateGraph(AgentState)
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_node("tools", tools_node)
graph_builder.set_entry_point("chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")

checkpointer = SQLAlchemyCheckpointSaver()
compiled_graph = graph_builder.compile(checkpointer=checkpointer)


class CheckpointedAgentWrapper:
    """
    Transparent proxy for CompiledStateGraph that ensures a thread_id
    is always present in configurable, allowing both thread-bound conversation
    sessions and direct standalone test invocations.
    """
    def __init__(self, inner):
        self._inner = inner

    def _ensure_config(self, config):
        c = dict(config or {})
        configurable = dict(c.get("configurable", {}))
        if "thread_id" not in configurable:
            configurable["thread_id"] = f"thread_{uuid.uuid4().hex[:8]}"
        c["configurable"] = configurable
        return c

    def invoke(self, input, config=None, **kwargs):
        return self._inner.invoke(input, config=self._ensure_config(config), **kwargs)

    async def ainvoke(self, input, config=None, **kwargs):
        return await self._inner.ainvoke(input, config=self._ensure_config(config), **kwargs)

    def stream(self, input, config=None, **kwargs):
        return self._inner.stream(input, config=self._ensure_config(config), **kwargs)

    def astream(self, input, config=None, **kwargs):
        return self._inner.astream(input, config=self._ensure_config(config), **kwargs)

    def get_state(self, config=None, **kwargs):
        return self._inner.get_state(self._ensure_config(config), **kwargs)

    def update_state(self, config=None, *args, **kwargs):
        return self._inner.update_state(self._ensure_config(config), *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._inner, name)


agent = CheckpointedAgentWrapper(compiled_graph)
