from functools import lru_cache
from fastapi import Depends
from firebase_admin import credentials, firestore, initialize_app
from google.cloud.firestore import Client
from .config import settings
from .logging_config import get_logger
from .services.fact_check_service import FactCheckerService

logger = get_logger()

@lru_cache()
def get_settings():
    """Cached settings instance."""
    return settings

@lru_cache()
def get_firebase_db() -> Client:
    """Initialize and cache a Firestore client."""
    cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
    try:
        initialize_app(cred)
    except ValueError:
        # App is already initialized
        pass
    return firestore.client()

@lru_cache()
def get_fact_checker_service() -> FactCheckerService:
    """Return a singleton FactCheckerService instance."""
    return FactCheckerService(
        openai_api_key=settings.OPENAI_API_KEY,
        google_api_key=settings.GOOGLE_API_KEY,
        logger=logger
    )

def get_logger_dep():
    """Provide a structured logger instance."""
    return logger