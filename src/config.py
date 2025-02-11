from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Firebase / Google
    GOOGLE_APPLICATION_CREDENTIALS: str
    GOOGLE_API_KEY: str

    # OpenAI
    OPENAI_API_KEY: str

    # Optional environment overrides
    ENVIRONMENT: Optional[str] = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()