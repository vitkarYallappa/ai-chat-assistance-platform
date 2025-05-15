import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.config import get_settings

# Context variables for request tracking
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
tenant_id: ContextVar[str] = ContextVar("tenant_id", default="")


class StructuredLogFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logs.
    
    Creates a JSON-formatted log entry with standardized fields like
    timestamp, log level, message, correlation ID, etc.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if available
        corr_id = correlation_id.get()
        if corr_id:
            log_data["correlation_id"] = corr_id
            
        # Add tenant ID if available
        t_id = tenant_id.get()
        if t_id:
            log_data["tenant_id"] = t_id
            
        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        # Add extra data if available
        if hasattr(record, "data") and isinstance(record.data, dict):
            log_data.update(record.data)
            
        return json.dumps(log_data)


def configure_logging() -> None:
    """
    Configure application-wide logging.
    
    Sets up structured JSON logging for production or formatted console
    logging for development, based on application settings.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    
    # Configure root logger
    root_logger.setLevel(log_level)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Use structured logging in production or when enabled
    if settings.ENABLE_STRUCTURED_LOGGING:
        formatter = StructuredLogFormatter()
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] [%(correlation_id)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Set specific module log levels if needed
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str, **extra: Any) -> logging.Logger:
    """
    Get a logger with the given name and extra context data.
    
    Args:
        name: Logger name, typically the module name
        **extra: Additional context data to include in log records
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Add a filter to inject correlation ID and extra data
    class ContextFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.correlation_id = correlation_id.get()
            if extra:
                record.data = extra
            return True
    
    logger.addFilter(ContextFilter())
    return logger


def set_correlation_id(corr_id: Optional[str] = None) -> str:
    """
    Set the correlation ID for the current context.
    
    Args:
        corr_id: Correlation ID to set. If None, a new UUID is generated.
    
    Returns:
        str: The correlation ID that was set
    """
    corr_id = corr_id or str(uuid.uuid4())
    correlation_id.set(corr_id)
    return corr_id


def set_tenant_id(t_id: str) -> None:
    """
    Set the tenant ID for the current context.
    
    Args:
        t_id: Tenant ID to set
    """
    tenant_id.set(t_id)