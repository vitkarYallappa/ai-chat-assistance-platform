"""
Interfaces package for the Adaptor Service.

This package contains all abstract base interfaces used by the adaptor service
to standardize interactions with external APIs.
"""

# Export all interfaces for easier imports
from .external_api import ExternalAPIAdaptorInterface, CapabilityType, APIStatus
from .connector import APIConnector, AuthType, HttpMethod, RequestConfig
from .normalizer import DataNormalizer, DataFormat
from .cache import CacheStrategy, CacheLevel, CacheTTLStrategy
from .fallback import FallbackHandler, FallbackStrategy

# Make these interfaces available when importing from the package
__all__ = [
    # External API interface
    'ExternalAPIAdaptorInterface',
    'CapabilityType',
    'APIStatus',
    
    # Connector interface
    'APIConnector',
    'AuthType',
    'HttpMethod',
    'RequestConfig',
    
    # Normalizer interface
    'DataNormalizer',
    'DataFormat',
    
    # Cache interface
    'CacheStrategy',
    'CacheLevel',
    'CacheTTLStrategy',
    
    # Fallback interface
    'FallbackHandler',
    'FallbackStrategy',
]