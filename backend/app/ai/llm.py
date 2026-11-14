"""Canonical model identities and provider construction. No implicit demo mode."""
from typing import Dict, Optional
from fastapi import HTTPException
from langchain_groq import ChatGroq
from app.core.config import get_settings
from app.ai.prompts import MASTER_PROMPTS, MODE_TEMPERATURES

PLAN_HIERARCHY = {"free": 0, "super": 1, "pro": 1, "hyper": 2}
PLAN_QUOTAS = {
    "free": {"tokens": 5000, "requests": 50},
    "super": {"tokens": 50000, "requests": 500},
    "pro": {"tokens": 50000, "requests": 500},
    "hyper": {"tokens": 500000, "requests": 5000},
}
# Production IDs checked against https://console.groq.com/docs/models on 2026-11-12.
MODEL_CATALOG = [
    {"id": "openai/gpt-oss-20b", "name": "GPT-OSS 20B",
     "description": "OpenAI open-weight model served by Groq.", "requiredPlan": "free"},
    {"id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B",
     "description": "Larger OpenAI open-weight model served by Groq.", "requiredPlan": "hyper"},
]
ALLOWED_MODELS = {m["id"]: m for m in MODEL_CATALOG}
# Compatibility for old clients: responses always disclose the resolved identity.
LEGACY_MODEL_IDS = {
    "llama3-8b-8192": "openai/gpt-oss-20b",
    "gemma-7b-it": "openai/gpt-oss-20b",
    "mixtral-8x7b-32768": "openai/gpt-oss-20b",
    "llama3-70b-8192": "openai/gpt-oss-120b",
}

CRAFT_MODES: Dict[str, str] = dict(MASTER_PROMPTS)


def is_tier_allowed(user_tier: str, required_tier: str) -> bool:
    return PLAN_HIERARCHY.get(user_tier.lower(), 0) >= PLAN_HIERARCHY[required_tier]


def resolve_model(tier: str, model_id: Optional[str] = None) -> str:
    resolved = LEGACY_MODEL_IDS.get(model_id, model_id) if model_id else "openai/gpt-oss-20b"
    entry = ALLOWED_MODELS.get(resolved)
    if not entry:
        raise HTTPException(422, "Unknown or unsupported model")
    if not is_tier_allowed(tier, entry["requiredPlan"]):
        raise HTTPException(403, f"Model requires the {entry['requiredPlan']} plan.")
    return resolved


def get_llm(tier: str = "free", model_id: Optional[str] = None,
            mode: str = "standard", **kwargs):
    settings = get_settings()
    key = (settings.groq_api_key or "").strip()
    if not key or key.startswith(("replace_with", "test-", "your_")):
        raise HTTPException(503, "AI provider is not configured. Please try again later.")
    mode_lower = (mode or "standard").lower()
    temperature = MODE_TEMPERATURES.get(mode_lower, 0.7)
    return ChatGroq(
        groq_api_key=key, model=resolve_model(tier, model_id), temperature=temperature,
        max_tokens=settings.max_output_tokens, timeout=settings.generation_timeout_seconds,
        max_retries=0, **kwargs,
    )
