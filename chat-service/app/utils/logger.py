import json
import logging
import sys
from typing import Dict, Any, Optional
import uuid

from app.config import get_settings

settings = get_settings()


class CustomJsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            str: JSON formatted log string
        """
        log_object = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "service": settings.SERVICE_NAME,
            "environment": settings.ENVIRONMENT,
        }
        
        # Add correlation_id if available
        if hasattr(record, "correlation_id"):
            log_object["correlation_id"] = record.correlation_id
            
        # Add extra attributes
        if hasattr(record, "extra"):
            log_object.update(record.extra)
            
        # Add exception info if available
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_object)


def configure_logging() -> None:
    """Configure global logging settings."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomJsonFormatter())
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=[handler],
        force=True
    )
    
    # Set levels for third-party loggers to reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Name for the logger
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Adapter for adding correlation ID and other context to logs.
    """
    
    def __init__(self, logger: logging.Logger, correlation_id: Optional[str] = None, extra: Optional[Dict[str, Any]] = None):
        """
        Initialize the logger adapter.
        
        Args:
            logger: Base logger to adapt
            correlation_id: Request correlation ID for distributed tracing
            extra: Extra fields to include in all logs
        """
        self.correlation_id = correlation_id or str(uuid.uuid4())
        extra_dict = extra or {}
        extra_dict["correlation_id"] = self.correlation_id
        super().__init__(logger, extra_dict)
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process the log message to add context data."""
        kwargs["extra"] = kwargs.get("extra", {})
        kwargs["extra"].update(self.extra)
        return msg, kwargs


def get_request_logger(name: str, correlation_id: Optional[str] = None, tenant_id: Optional[str] = None) -> LoggerAdapter:
    """
    Get a logger configured with request context.
    
    Args:
        name: Logger name
        correlation_id: Request correlation ID for tracing
        tenant_id: Tenant identifier for multi-tenant context
        
    Returns:
        LoggerAdapter: Configured logger adapter
    """
    logger = get_logger(name)
    extra = {}
    if tenant_id:
        extra["tenant_id"] = tenant_id
        
    return LoggerAdapter(logger, correlation_id, extra)