from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    The state for the LangGraph agent.
    `messages` contains a list of BaseMessage objects.
    `add_messages` ensures new messages are appended rather than overwritten.
    """
    messages: Annotated[list[BaseMessage], add_messages]
