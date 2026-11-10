from typing import Optional
from langchain_groq import ChatGroq
from app.core.config import get_settings

ALLOWED_MODELS = {
    "llama-3.1-8b-instant": {"required_tier": "free"},
    "llama3-8b-8192": {"required_tier": "free"},
    "gemma2-9b-it": {"required_tier": "free"},
    "gemma-7b-it": {"required_tier": "free"},
    "mixtral-8x7b-32768": {"required_tier": "super"},
    "llama-3.3-70b-versatile": {"required_tier": "hyper"},
    "llama3-70b-8192": {"required_tier": "hyper"},
}

def get_llm(tier: str = "free", model_id: Optional[str] = None):
    """
    Initialize and return the Groq LLM model based on user tier and requested model_id.
    """
    settings = get_settings()
    tier_lower = tier.lower()
    if model_id and model_id in ALLOWED_MODELS:
        model_name = model_id
    else:
        model_name = "llama-3.3-70b-versatile" if tier_lower in ("pro", "super", "hyper") else "llama-3.1-8b-instant"
    
    return ChatGroq(
        groq_api_key=settings.groq_api_key,
        model=model_name,
        temperature=0.7,
        max_tokens=1024
    )

