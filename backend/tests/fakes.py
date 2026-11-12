import asyncio
import threading
from typing import Any
from pydantic import Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


class ProviderFake(BaseChatModel):
    failure: str | None = None
    text: str = "Hello from the offline test provider."
    calls: int = 0
    hold: bool = False
    cancelled: Any = Field(default_factory=threading.Event)
    release: Any = Field(default_factory=threading.Event)

    @property
    def _llm_type(self):
        return "offline-provider"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls += 1
        if self.failure:
            raise RuntimeError(self.failure)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(
            content=self.text, usage_metadata={"input_tokens": 20, "output_tokens": 22, "total_tokens": 42}
        ))])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls += 1
        if self.failure:
            raise RuntimeError(self.failure)
        try:
            yield ChatGenerationChunk(message=AIMessageChunk(content=self.text))
            while self.hold and not self.release.is_set():
                await asyncio.sleep(0.01)
            yield ChatGenerationChunk(message=AIMessageChunk(
                content="", usage_metadata={"input_tokens": 20, "output_tokens": 22, "total_tokens": 42}
            ))
        finally:
            self.cancelled.set()
