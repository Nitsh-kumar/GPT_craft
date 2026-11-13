import asyncio
import threading
from typing import Any, List, Optional
from pydantic import Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
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

    def bind_tools(self, tools, **kwargs):
        return self

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


class AgentToolFake(BaseChatModel):
    """Offline test fake supporting system-prompt memory checks and Agent Studio tool calls."""
    mode: str = "standard"
    model_name: str = "openai/gpt-oss-20b"
    bound_tools: List[Any] = Field(default_factory=list)
    failure: Optional[str] = None
    calls: int = 0

    @property
    def _llm_type(self):
        return "offline-agent-tool-fake"

    def bind_tools(self, tools, **kwargs):
        return AgentToolFake(
            mode=self.mode,
            model_name=self.model_name,
            bound_tools=list(tools),
            failure=self.failure,
        )

    def _build_reply(self, messages: List[BaseMessage]) -> str:
        last_user = ""
        system_text = ""
        tool_observation = ""
        for msg in messages:
            msg_type = getattr(msg, "type", "")
            if msg_type == "system":
                system_text = str(msg.content)
            elif msg_type == "human":
                last_user = str(msg.content)
            elif msg_type == "tool":
                tool_observation = str(msg.content)

        reply = f"### GPTCraft ({self.mode.capitalize()} Mode • `{self.model_name}`)\n\nProcessed: {last_user[:120]}\n\n"
        if "User Personalization & Persistent Context" in system_text:
            snippet = system_text.split("## User Personalization & Persistent Context", 1)[1]
            snippet = snippet.split("### Behavioral Personalization Rules:", 1)[0].strip()
            reply += f"> **Personalization Active**\n\n{snippet}\n\n"
        if self.mode == "agent":
            reply += "#### Agent Studio Execution Plan\n1. Scoped within workspace boundaries.\n"
            if tool_observation:
                reply += f"\n#### Workspace Observation\n{tool_observation[:250].strip()}\n"
                if "rejected" in tool_observation.lower():
                    reply += f"\n#### Re-planning Action\nI acknowledged your rejection: {tool_observation[:200]}"
        return reply

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls += 1
        if self.failure:
            raise RuntimeError(self.failure)
        if self.mode == "agent" and self.bound_tools and messages and getattr(messages[-1], "type", "") == "human":
            prompt = str(messages[-1].content)
            prompt_lower = prompt.lower()
            if any(k in prompt_lower for k in ("edit", "modify", "create", "update", "write")):
                target_path = "docs/test_edit.txt"
                for word in prompt.split():
                    clean_word = word.strip("\"'`;,")
                    if "/" in clean_word or clean_word.endswith((".txt", ".md", ".py", ".json")):
                        target_path = clean_word
                        break
                msg = AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "edit_workspace_file",
                        "args": {
                            "path": target_path,
                            "content": "Updated content from Agent Studio",
                            "mode": "write",
                            "rationale": "Applying requested file changes.",
                        },
                        "id": "call_edit_1",
                    }],
                    usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                )
                return ChatResult(generations=[ChatGeneration(message=msg)])
            if any(k in prompt_lower for k in ("terminal", "command", "bash", "shell", "run test", "run pytest", "execute command")):
                cmd = "pytest tests/test_api.py" if "pytest" in prompt_lower else "python -c \"print('Hello from terminal')\""
                msg = AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "run_terminal_command",
                        "args": {"command": cmd, "rationale": "Executing test/lint command in workspace."},
                        "id": "call_cmd_1",
                    }],
                    usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                )
                return ChatResult(generations=[ChatGeneration(message=msg)])
            if any(k in prompt_lower for k in ("read", "glossary", "readme")):
                target = "GLOSSARY.md" if "glossary" in prompt_lower else "README.md"
                msg = AIMessage(
                    content="",
                    tool_calls=[{"name": "read_workspace_file", "args": {"path": target, "start_line": 1, "end_line": 50}, "id": "call_read_1"}],
                    usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                )
                return ChatResult(generations=[ChatGeneration(message=msg)])
            if any(k in prompt_lower for k in ("search", "symbol", "find")):
                msg = AIMessage(
                    content="",
                    tool_calls=[{"name": "search_workspace_symbols", "args": {"query": "ChatService", "path": "backend"}, "id": "call_search_1"}],
                    usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                )
                return ChatResult(generations=[ChatGeneration(message=msg)])
            if "inspect" in prompt_lower or "files" in prompt_lower or "directory" in prompt_lower:
                msg = AIMessage(
                    content="",
                    tool_calls=[{"name": "list_workspace_directory", "args": {"path": "."}, "id": "call_list_1"}],
                    usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
                )
                return ChatResult(generations=[ChatGeneration(message=msg)])

        reply = self._build_reply(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(
            content=reply,
            usage_metadata={"input_tokens": 12, "output_tokens": 24, "total_tokens": 36},
        ))])
