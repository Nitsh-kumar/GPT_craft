from typing import List, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from app.ai.graph.state import AgentState
from app.ai.llm import get_llm, CRAFT_MODES, LocalCraftLLM

# Define tools here
tools = []

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
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    try:
        response = llm_with_tools.invoke(messages)
    except Exception as exc:
        err_str = str(exc).lower()
        if "model" in err_str or "not found" in err_str or "decommissioned" in err_str or "connect" in err_str:
            fallback = LocalCraftLLM(model_name=model_id or "gptcraft", mode=mode)
            response = fallback.invoke(messages)
        else:
            raise exc

    return {"messages": [response]}


# Define the graph
graph_builder = StateGraph(AgentState)

# Add nodes
graph_builder.add_node("chatbot", chatbot_node)

# Set entry point
graph_builder.set_entry_point("chatbot")

# Add edges
graph_builder.add_edge("chatbot", END)

# Compile the agent
agent = graph_builder.compile()
