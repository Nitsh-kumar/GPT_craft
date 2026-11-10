from typing import Optional, Dict, Any, List
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_groq import ChatGroq
from app.core.config import get_settings

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

CRAFT_MODES: Dict[str, str] = {
    "standard": (
        "You are GPTCraft, an intelligent thinking partner. Provide clear, accurate, "
        "and well-structured markdown responses."
    ),
    "architect": (
        "You are GPTCraft in Deep Architect Mode. Break complex problems down into "
        "system architecture, trade-offs, data flow, and clean production-grade code."
    ),
    "code": (
        "You are GPTCraft in Code Craft Mode. Prioritize clean, idiomatic, well-typed "
        "code with concise explanations and edge-case handling."
    ),
    "brainstorm": (
        "You are GPTCraft in Creative Brainstorm Mode. Generate high-leverage ideas, "
        "unique angles, structured comparisons, and actionable next steps."
    ),
}


class LocalCraftLLM:
    """
    Deterministic local fallback responder used when GROQ_API_KEY is not configured
    or set to a placeholder in local development / E2E browser testing.
    Supports `.bind_tools()` and `.invoke()` matching LangChain ChatModel interface.
    """

    def __init__(self, model_name: str, mode: str = "standard"):
        self.model_name = model_name
        self.mode = mode

    def bind_tools(self, tools: list):
        return self

    def invoke(self, messages: List[BaseMessage]) -> AIMessage:
        last_user = ""
        for msg in reversed(messages):
            if msg.type == "human":
                last_user = str(msg.content)
                break

        mode_label = self.mode.capitalize()
        reply = (
            f"### GPTCraft ({mode_label} Mode • `{self.model_name}`)\n\n"
            f"I processed your request: **\"{last_user[:120]}\"**\n\n"
            f"#### Key Architectural Insights\n"
            f"- **Context Retention**: Multi-turn conversation state managed via **LangGraph**.\n"
            f"- **Tier & Quota Policy**: Verified active plan and token budget.\n\n"
            f"```python\n"
            f"def gptcraft_pipeline(prompt: str, mode: str = '{self.mode}') -> dict:\n"
            f"    return {{'status': 'verified', 'model': '{self.model_name}', 'mode': mode}}\n"
            f"```"
        )
        tokens = max(24, len(last_user.split()) * 2 + 40)
        return AIMessage(
            content=reply,
            response_metadata={"token_usage": {"total_tokens": tokens}},
        )


def is_tier_allowed(user_tier: str, required_tier: str) -> bool:
    u_rank = PLAN_HIERARCHY.get(user_tier.lower(), 0)
    r_rank = PLAN_HIERARCHY.get(required_tier.lower(), 0)
    return u_rank >= r_rank


def get_llm(tier: str = "free", model_id: Optional[str] = None, mode: str = "standard"):
    """
    Initialize and return the Groq LLM model (or LocalCraftLLM fallback if no real key is configured)
    based on user tier, requested model_id, and Craft mode.
    """
    settings = get_settings()
    tier_lower = tier.lower()

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
        return LocalCraftLLM(model_name=model_id or model_name, mode=mode)

    return ChatGroq(
        groq_api_key=api_key,
        model=model_name,
        temperature=0.7,
        max_tokens=1024,
    )
