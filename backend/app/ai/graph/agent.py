from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from app.ai.graph.state import AgentState
from app.ai.llm import get_llm, CRAFT_MODES, LocalCraftLLM

# Define tools here
tools = []


def chatbot_node(state: AgentState, config: RunnableConfig):
    """
    The main node representing the chatbot's reasoning with Craft Mode system prompts.
    """
    configurable = config.get("configurable", {})
    user_tier = configurable.get("user_tier", "free")
    model_id = configurable.get("model_id")
    mode = (configurable.get("mode") or "standard").lower()

    system_prompt = CRAFT_MODES.get(mode, CRAFT_MODES["standard"])
    llm = get_llm(tier=user_tier, model_id=model_id, mode=mode)
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
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
