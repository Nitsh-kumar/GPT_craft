import uuid
from typing import List, Optional
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from app.ai.graph.state import AgentState
from app.ai.llm import get_llm, CRAFT_MODES, LocalCraftLLM
from app.ai.tools.workspace import TIER_1_TOOLS, TIER_2_TOOLS, run_terminal_command

# Define tools here (Tier 1 read-only tools + Tier 2 HITL file & terminal mutation tools)
tools = list(TIER_1_TOOLS) + list(TIER_2_TOOLS)

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


def chatbot_node(state: AgentState, config: RunnableConfig):
    """
    The main reasoning node:
    - Merges Craft Mode master prompts with active user personalization & memory context from AgentState.
    - Applies a sliding message window to optimize token budget.
    - Invokes mode-calibrated LLM with graceful fallback.
    """
    configurable = config.get("configurable", {})
    user_tier = configurable.get("user_tier", "free")
    model_id = configurable.get("model_id")
    mode = (configurable.get("mode") or "standard").lower()

    base_system_prompt = CRAFT_MODES.get(mode, CRAFT_MODES["standard"])
    personalization_block = build_personalization_block(
        state.get("user_instructions"),
        state.get("relevant_memories"),
    )
    full_system_prompt = base_system_prompt + personalization_block

    raw_messages = list(state.get("messages", []))
    if len(raw_messages) > MAX_CONTEXT_MESSAGES:
        trimmed_messages = raw_messages[-MAX_CONTEXT_MESSAGES:]
    else:
        trimmed_messages = raw_messages

    messages = [SystemMessage(content=full_system_prompt)] + trimmed_messages

    llm = get_llm(tier=user_tier, model_id=model_id, mode=mode)
    llm_with_tools = llm.bind_tools(tools) if (mode == "agent" and tools) else llm

    try:
        response = llm_with_tools.invoke(messages)
    except Exception as exc:
        err_str = str(exc).lower()
        if "model" in err_str or "not found" in err_str or "decommissioned" in err_str or "connect" in err_str:
            fallback = LocalCraftLLM(model_name=model_id or "gptcraft", mode=mode)
            fallback_with_tools = fallback.bind_tools(tools) if (mode == "agent" and tools) else fallback
            response = fallback_with_tools.invoke(messages)
        else:
            raise exc

    return {"messages": [response]}


# Define the graph
graph_builder = StateGraph(AgentState)

# Add nodes
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_node("tools", ToolNode(tools))

# Set entry point
graph_builder.set_entry_point("chatbot")

# Add conditional edges
graph_builder.add_conditional_edges("chatbot", tools_condition)

# Add cyclical edge back to chatbot
graph_builder.add_edge("tools", "chatbot")

# Compile the agent with in-memory checkpointing for HITL interrupts
checkpointer = MemorySaver()
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

    def stream(self, input, config=None, **kwargs):
        return self._inner.stream(input, config=self._ensure_config(config), **kwargs)

    def get_state(self, config=None, **kwargs):
        return self._inner.get_state(self._ensure_config(config), **kwargs)

    def update_state(self, config=None, *args, **kwargs):
        return self._inner.update_state(self._ensure_config(config), *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._inner, name)


agent = CheckpointedAgentWrapper(compiled_graph)
