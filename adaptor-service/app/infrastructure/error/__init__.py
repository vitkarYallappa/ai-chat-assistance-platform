"""
Error handling package for the Adaptor Service.
Provides centralized error processing, categorization, and fallback mechanisms.
"""

from app.infrastructure.error.handler import (
    ErrorHandler,
    ErrorDetails,
    ErrorCategory,
    ErrorSeverity
)

from app.infrastructure.error.fallback import (
    FallbackHandler,
    FallbackMetadata,
    FallbackEntry,
    FallbackRegistry
)

__all__ = [
    # Error handler exports
    "ErrorHandler",
    "ErrorDetails",
    "ErrorCategory",
    "ErrorSeverity",
    
    # Fallback handler exports
    "FallbackHandler",
    "FallbackMetadata",
    "FallbackEntry",
    "FallbackRegistry",
]