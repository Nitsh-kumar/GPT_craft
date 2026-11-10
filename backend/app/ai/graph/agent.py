from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.ai.graph.state import AgentState
from app.ai.llm import get_llm

# Define tools here
tools = []

from langchain_core.runnables import RunnableConfig

def chatbot_node(state: AgentState, config: RunnableConfig):
    """
    The main node representing the chatbot's reasoning.
    """
    user_tier = config.get("configurable", {}).get("user_tier", "free")
    llm = get_llm(tier=user_tier)
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# Define the graph
graph_builder = StateGraph(AgentState)

# Add nodes
graph_builder.add_node("chatbot", chatbot_node)

# Set entry point
graph_builder.set_entry_point("chatbot")

# Add edges (Since we have no tools yet, just end after chatbot)
graph_builder.add_edge("chatbot", END)

# Compile the agent
agent = graph_builder.compile()
