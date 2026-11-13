from typing import Annotated, TypedDict, Optional, List
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    """
    The state for the LangGraph agent.
    `messages` contains a list of BaseMessage objects.
    `add_messages` ensures new messages are appended rather than overwritten.
    `user_instructions` and `relevant_memories` carry per-user personalization context.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    user_instructions: Optional[str]
    relevant_memories: Optional[List[str]]
