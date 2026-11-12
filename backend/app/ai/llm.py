from typing import Optional, Dict, Any, List, Generator
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, SystemMessage
from langchain_groq import ChatGroq
from app.core.config import get_settings
from app.ai.prompts import MASTER_PROMPTS, MODE_TEMPERATURES

PLAN_HIERARCHY = {
    "free": 0,
    "super": 1,
    "pro": 1,
    "hyper": 2,
}

PLAN_QUOTAS = {
    "free": {"tokens": 5000, "requests": 50},
    "super": {"tokens": 50000, "requests": 500},
    "pro": {"tokens": 50000, "requests": 500},
    "hyper": {"tokens": 500000, "requests": 5000},
}

MODEL_CATALOG: List[Dict[str, str]] = [
    {
        "id": "llama3-8b-8192",
        "name": "Llama 3 8B",
        "description": "Fast, efficient, and versatile for daily tasks.",
        "requiredPlan": "free",
        "groq_model": "openai/gpt-oss-20b",
    },
    {
        "id": "gemma-7b-it",
        "name": "Gemma 2 9B",
        "description": "Google-grade lightweight model optimization.",
        "requiredPlan": "free",
        "groq_model": "qwen/qwen3.8-27b",
    },
    {
        "id": "mixtral-8x7b-32768",
        "name": "Mixtral 8x7B",
        "description": "Powerful mixture of experts for complex reasoning.",
        "requiredPlan": "super",
        "groq_model": "qwen/qwen3.8-27b",
    },
    {
        "id": "llama3-70b-8192",
        "name": "Llama 3.3 70B",
        "description": "Groq's most capable reasoning and coding model.",
        "requiredPlan": "hyper",
        "groq_model": "openai/gpt-oss-120b",
    },
]

ALLOWED_MODELS = {m["id"]: m for m in MODEL_CATALOG}

# Production Craft Mode Prompts
CRAFT_MODES: Dict[str, str] = MASTER_PROMPTS


class LocalCraftLLM:
    """
    Deterministic local fallback responder used when GROQ_API_KEY is not configured
    or set to a placeholder in local development / E2E browser testing.
    Supports `.bind_tools()`, `.invoke()`, and `.stream()` matching LangChain ChatModel interface.
    """

    def __init__(
        self,
        model_name: str,
        mode: str = "standard",
        bound_tools: Optional[list] = None,
    ):
        self.model_name = model_name
        self.mode = mode.lower()
        self._bound_tools = list(bound_tools or [])

    def bind_tools(self, tools: list):
        return LocalCraftLLM(
            model_name=self.model_name,
            mode=self.mode,
            bound_tools=tools,
        )

    def _generate_content(self, messages: List[BaseMessage]) -> str:
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

        mode_label = self.mode.capitalize()
        has_memory = "User Personalization & Persistent Context" in system_text

        reply = (
            f"### GPTCraft ({mode_label} Mode • `{self.model_name}`)\n\n"
            f"I processed your request: **\"{last_user[:120]}\"**\n\n"
        )

        if has_memory:
            context_snippet = system_text.split("## User Personalization & Persistent Context", 1)[1]
            context_snippet = context_snippet.split("### Behavioral Personalization Rules:", 1)[0].strip()
            reply += (
                f"> **Personalization Active**: Applied your custom instructions and persistent memory "
                f"to tailor this response.\n\n"
                f"{context_snippet}\n\n"
            )

        if self.mode == "code":
            reply += (
                f"```python\n"
                f"# Verified implementation tailored to your preferences\n"
                f"def gptcraft_solution(query: str) -> dict:\n"
                f"    return {{\n"
                f"        'status': 'success',\n"
                f"        'query': query,\n"
                f"        'mode': 'code',\n"
                f"        'personalized': {has_memory}\n"
                f"    }}\n\n"
                f"if __name__ == '__main__':\n"
                f"    print(gptcraft_solution('{last_user[:30]}'))\n"
                f"```"
            )
        elif self.mode == "architect":
            reply += (
                f"#### System Architecture & Flow\n"
                f"```mermaid\n"
                f"flowchart TD\n"
                f"    Client[User Client] --> API[FastAPI Gateway]\n"
                f"    API --> Memory[Memory & Relevance Engine]\n"
                f"    API --> LLM[LangGraph Orchestration]\n"
                f"    LLM --> Client\n"
                f"```\n\n"
                f"- **Data Flow**: Low-latency retrieval with in-database token ranking.\n"
                f"- **Fault Domain**: Self-contained with zero external cloud dependencies."
            )
        elif self.mode == "brainstorm":
            reply += (
                f"#### Strategic Opportunities\n"
                f"| Vector | Opportunity | Impact | Feasibility |\n"
                f"| :--- | :--- | :--- | :--- |\n"
                f"| **Quick Win** | Dynamic Context Caching | High | Immediate |\n"
                f"| **High Leverage** | Hybrid Memory Indexing | Very High | High |\n"
                f"| **Moonshot** | Autonomous Goal Agents | Transformative | Medium |"
            )
        elif self.mode == "agent":
            reply += (
                f"#### Agent Studio Execution Plan\n"
                f"1. **Goal Analysis**: Scoped request within workspace boundaries.\n"
                f"2. **Safety Policy**: Tier 1 read-only checks auto-approved; Tier 2/3 mutations gated by HITL.\n"
                f"3. **Outcome**: Agent Studio protocol envelope ready for autonomous turn execution."
            )
            if tool_observation:
                obs_snippet = tool_observation[:250].strip()
                reply += (
                    f"\n\n#### Workspace Observation\n"
                    f"```text\n{obs_snippet}\n```"
                )
                if "rejected" in tool_observation.lower():
                    reply += (
                        f"\n\n#### Re-planning Action\n"
                        f"I acknowledged your rejection. Re-planning next steps based on user feedback: {obs_snippet}"
                    )
        else:
            reply += (
                f"#### Core Insights\n"
                f"- **Context Retention**: Multi-turn conversation state managed seamlessly via **LangGraph**.\n"
                f"- **Adaptive Personalization**: Responses automatically calibrated to your active technical profile."
            )

        return reply

    def invoke(self, messages: List[BaseMessage]) -> AIMessage:
        if self.mode == "agent" and self._bound_tools:
            last_msg = messages[-1] if messages else None
            if last_msg and getattr(last_msg, "type", "") == "human":
                prompt_lower = str(last_msg.content).lower()
                if any(k in prompt_lower for k in ("edit", "modify", "create", "update", "write")):
                    tool_name = "edit_workspace_file"
                    target_path = "docs/test_edit.txt"
                    for word in str(last_msg.content).split():
                        clean_word = word.strip("\"'`;,")
                        if "/" in clean_word or clean_word.endswith((".txt", ".md", ".py", ".json")):
                            target_path = clean_word
                            break
                    tool_args = {
                        "path": target_path,
                        "content": "Updated content from Agent Studio",
                        "mode": "write",
                        "rationale": "Applying requested file changes.",
                    }
                    call_id = "call_edit_1"
                elif "read" in prompt_lower or "glossary" in prompt_lower or "readme" in prompt_lower:
                    tool_name = "read_workspace_file"
                    target = "GLOSSARY.md" if "glossary" in prompt_lower else "README.md"
                    tool_args = {"path": target, "start_line": 1, "end_line": 50}
                    call_id = "call_read_1"
                elif "search" in prompt_lower or "symbol" in prompt_lower or "find" in prompt_lower:
                    tool_name = "search_workspace_symbols"
                    tool_args = {"query": "ChatService", "path": "backend"}
                    call_id = "call_search_1"
                else:
                    tool_name = "list_workspace_directory"
                    tool_args = {"path": "."}
                    call_id = "call_list_1"

                return AIMessage(
                    content="",
                    tool_calls=[{
                        "name": tool_name,
                        "args": tool_args,
                        "id": call_id,
                    }],
                    response_metadata={"token_usage": {"total_tokens": 30}},
                )

        reply = self._generate_content(messages)
        last_user = ""
        for msg in reversed(messages):
            if msg.type == "human":
                last_user = str(msg.content)
                break
        tokens = max(24, len(last_user.split()) * 2 + len(reply.split()))
        return AIMessage(
            content=reply,
            response_metadata={"token_usage": {"total_tokens": tokens}},
        )

    def stream(self, messages: List[BaseMessage]) -> Generator[AIMessageChunk, None, None]:
        reply = self._generate_content(messages)
        words = reply.split(" ")
        for idx, word in enumerate(words):
            chunk_content = (" " if idx > 0 else "") + word
            yield AIMessageChunk(content=chunk_content)


def is_tier_allowed(user_tier: str, required_tier: str) -> bool:
    u_rank = PLAN_HIERARCHY.get(user_tier.lower(), 0)
    r_rank = PLAN_HIERARCHY.get(required_tier.lower(), 0)
    return u_rank >= r_rank


def get_llm(tier: str = "free", model_id: Optional[str] = None, mode: str = "standard"):
    """
    Initialize and return the Groq LLM model (or LocalCraftLLM fallback if no real key is configured)
    based on user tier, requested model_id, and Craft mode with calibrated temperature.
    """
    settings = get_settings()
    tier_lower = tier.lower()
    mode_lower = (mode or "standard").lower()

    if model_id and model_id in ALLOWED_MODELS:
        entry = ALLOWED_MODELS[model_id]
        model_name = entry["groq_model"]
    else:
        model_name = (
            "openai/gpt-oss-120b"
            if tier_lower in ("pro", "super", "hyper")
            else "openai/gpt-oss-20b"
        )

    api_key = (settings.groq_api_key or "").strip()
    is_placeholder = (
        not api_key
        or api_key.startswith("replace_with")
        or api_key.startswith("test-")
        or api_key == "your_groq_api_key"
    )

    if is_placeholder:
        return LocalCraftLLM(model_name=model_id or model_name, mode=mode_lower)

    temperature = MODE_TEMPERATURES.get(mode_lower, 0.7)

    return ChatGroq(
        groq_api_key=api_key,
        model=model_name,
        temperature=temperature,
        max_tokens=1024,
    )
