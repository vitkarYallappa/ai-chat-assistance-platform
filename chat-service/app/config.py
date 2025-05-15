from functools import lru_cache
from typing import Optional, Dict, Any
from pydantic import BaseSettings, validator
import os
from dotenv import load_dotenv


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Service information
    SERVICE_NAME: str = "chat-service"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    
    # FastAPI configuration
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    
    # Database configuration
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_TIMEOUT: int = 30
    
    # Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AI model configuration
    DEFAULT_MODEL: str = "gpt-4"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 1024
    
    # Vector search configuration
    VECTOR_DB_URL: Optional[str] = None
    VECTOR_DIMENSION: int = 1536
    
    # External services
    ADAPTOR_SERVICE_URL: str
    MCP_SERVICE_URL: str
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    
    # Cache configuration
    REDIS_URL: Optional[str] = None
    CACHE_TTL_SECONDS: int = 3600
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v: str) -> str:
        """Validate that database URL is properly formatted."""
        if not v.startswith(("postgresql://", "mongodb://", "sqlite://")):
            raise ValueError("Database URL must be a valid connection string")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


def load_env_file() -> None:
    """Load environment variables from .env file if it exists."""
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)


@lru_cache
def get_settings() -> Settings:
    """
    Create and cache application settings.
    
    Returns:
        Settings: Application settings instance
    """
    load_env_file()
    return Settings()