from functools import lru_cache
from typing import Any, Dict, Optional
from pydantic import BaseSettings, validator
import os
from dotenv import load_dotenv


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Adaptor Service"
    DEBUG: bool = False
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    
    # Database settings
    DATABASE_URI: Optional[str] = None
    
    # Cache settings
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL: int = 3600  # Default cache TTL in seconds
    
    # Authentication settings
    SECRET_KEY: str = "CHANGEME_IN_PRODUCTION"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    ENABLE_STRUCTURED_LOGGING: bool = True
    
    # Tenant settings
    DEFAULT_TENANT_ID: str = "default"
    
    # External API timeout settings
    DEFAULT_TIMEOUT: int = 10  # seconds
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 0.3
    
    # Integration settings
    ADAPTOR_REGISTRY_ENABLED: bool = True
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


def load_env_file(env_file: str = ".env") -> None:
    """
    Load environment variables from specified .env file.
    
    Args:
        env_file: Path to the .env file. Defaults to ".env".
    """
    env_path = os.path.join(os.getcwd(), env_file)
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print(f"Warning: Environment file {env_path} not found")


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings with caching for efficiency.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()