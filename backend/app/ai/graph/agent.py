"""Async graph: native model chunks propagate through stream_mode='messages'."""
import asyncio
import httpx
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from app.ai.graph.state import AgentState
from app.ai.llm import get_llm, CRAFT_MODES
from app.core.config import get_settings


async def chatbot_node(state: AgentState, config: RunnableConfig):
    options = config.get("configurable", {})
    mode = options.get("mode", "standard")
    # Request-scoped transport closes sockets even when the graph is cancelled.
    async with httpx.AsyncClient(timeout=get_settings().generation_timeout_seconds) as transport:
        llm = get_llm(tier=options.get("user_tier", "free"),
                      model_id=options.get("model_id"), mode=mode,
                      http_async_client=transport)
        generation = asyncio.create_task(llm.ainvoke(
            [SystemMessage(content=CRAFT_MODES[mode]), *state["messages"]], config=config
        ))
        cancelled = asyncio.create_task(options["cancel_event"].wait())
        try:
            done, _ = await asyncio.wait(
                [generation, cancelled], timeout=get_settings().generation_timeout_seconds,
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


graph_builder = StateGraph(AgentState)
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.set_entry_point("chatbot")
graph_builder.add_edge("chatbot", END)
agent = graph_builder.compile()
