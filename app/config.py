import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Data Assistant"
    UPLOAD_DIR: str = "data/uploads"

    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-oss-120b"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
