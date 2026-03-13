from langchain_groq import ChatGroq
from app.core.config import get_settings

def get_llm():
    """
    Initialize and return the Groq LLM model.
    """
    settings = get_settings()
    return ChatGroq(
        groq_api_key=settings.groq_api_key,
        model="llama3-8b-8192", # Default, can be changed based on need
        temperature=0.7,
        max_tokens=1024
    )
