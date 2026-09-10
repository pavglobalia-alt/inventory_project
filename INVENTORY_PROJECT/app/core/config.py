import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Inventory Management System"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "super-secret-key-change-in-production-1234567890!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database settings: sqlite fallback if PostgreSQL URL not provided
    DATABASE_URL: str = "sqlite:///./inventory.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
