import os
from dotenv import load_dotenv
from fastapi import HTTPException
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings


def get_llm(temperature: float = 0.0) -> BaseChatModel:
    load_dotenv(override=True)

    api_key = (
        os.getenv("GROQ_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or settings.GROQ_API_KEY
        or settings.OPENAI_API_KEY
        or ""
    ).strip()

    model_name = (
        os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or settings.LLM_MODEL
        or "openai/gpt-oss-120b"
    ).strip()

    if not api_key or "paste_your" in api_key or api_key.startswith("sk-your"):
        raise HTTPException(
            status_code=400,
            detail="Missing Groq API Key! Set your GROQ_API_KEY in .env or the sidebar.",
        )

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=temperature,
    )
