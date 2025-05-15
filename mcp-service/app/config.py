from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional, Union
import os
from pathlib import Path

class LoggingSettings(BaseSettings):
    """Logging-specific configuration settings."""
    LEVEL: str = "INFO"
    FORMAT: str = "json"
    CORRELATION_ID_HEADER: str = "X-Correlation-ID"
    
    class Config:
        env_prefix = "LOGGING_"

class DatabaseSettings(BaseSettings):
    """Database-specific configuration settings."""
    URI: str
    MAX_CONNECTIONS: int = 10
    TIMEOUT: int = 30
    
    class Config:
        env_prefix = "DB_"

class ChannelSettings(BaseSettings):
    """Channel-specific configuration settings."""
    WHATSAPP_ENABLED: bool = True
    FACEBOOK_ENABLED: bool = True
    TELEGRAM_ENABLED: bool = True
    WEBCHAT_ENABLED: bool = True
    
    class Config:
        env_prefix = "CHANNEL_"

class WebSocketSettings(BaseSettings):
    """WebSocket-specific configuration settings."""
    MAX_CONNECTIONS: int = 10000
    HEARTBEAT_INTERVAL: int = 30
    CONNECTION_TIMEOUT: int = 60
    
    class Config:
        env_prefix = "WS_"

class SecuritySettings(BaseSettings):
    """Security-specific configuration settings."""
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    WEBHOOK_SECRET_HEADER: str = "X-Webhook-Secret"
    
    class Config:
        env_prefix = "SECURITY_"

class Settings(BaseSettings):
    """Main application settings."""
    APP_NAME: str = "mcp-service"
    ENV: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["*"]
    
    # Services URLs
    CHAT_SERVICE_URL: str
    
    # Nested settings
    logging: LoggingSettings = LoggingSettings()
    database: DatabaseSettings = DatabaseSettings()
    channel: ChannelSettings = ChannelSettings()
    websocket: WebSocketSettings = WebSocketSettings()
    security: SecuritySettings = SecuritySettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

def load_env_file() -> None:
    """
    Load environment variables from .env file based on the environment.
    
    Priority:
    1. .env.{ENV}.local
    2. .env.{ENV}
    3. .env.local
    4. .env
    """
    env = os.getenv("ENV", "development")
    env_files = [
        f".env.{env}.local",
        f".env.{env}",
        ".env.local",
        ".env"
    ]
    
    for env_file in env_files:
        env_path = Path(env_file)
        if env_path.exists():
            # Use Pydantic's load method instead of a direct load
            # to ensure proper parsing and validation
            return

@lru_cache()
def get_settings() -> Settings:
    """
    Returns cached application settings.
    
    Using lru_cache to avoid re-reading environment variables on each call.
    """
    load_env_file()
    return Settings()