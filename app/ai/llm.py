import os
from langchain_groq import ChatGroq

def get_llm():
    """
    Initialize and return the Groq LLM model.
    Make sure GROQ_API_KEY is set in your environment variables.
    """
    return ChatGroq(
        model="llama3-8b-8192", # Default, can be changed based on need
        temperature=0.7,
        max_tokens=1024
    )
