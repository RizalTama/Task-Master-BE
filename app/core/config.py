from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-5"
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    
    # JWT settings
    JWT_SECRET_KEY: str = "a_very_secret_key"  # Should be loaded from .env in a real app
    JWT_ALGORITHM: str = "HS256"
    
    # Firebase Web API Key for REST API calls
    FIREBASE_API_KEY: str = "your_firebase_web_api_key" # Should be loaded from .env

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()

# penting: agar firebase-admin baca credential json
if settings.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
