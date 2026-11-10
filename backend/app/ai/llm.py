from langchain_groq import ChatGroq
from app.core.config import get_settings

def get_llm(tier: str = "free"):
    """
    Initialize and return the Groq LLM model based on user tier.
    """
    settings = get_settings()
    model_name = "llama-3.3-70b-versatile" if tier == "pro" else "llama-3.1-8b-instant"
    
    return ChatGroq(
        groq_api_key=settings.groq_api_key,
        model=model_name,
        temperature=0.7,
        max_tokens=1024
    )
