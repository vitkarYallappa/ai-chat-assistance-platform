"""
Adapters package for the Adaptor Service.

This package contains components for integrating with external APIs, including:
- Abstract interfaces that define the contracts for adapters
- Concrete implementations for specific external APIs
- Factory and registry for managing adapter instances
"""

# Import the interfaces subpackage to make it available
from . import interfaces

# Import core adapter components
from .factory import AdaptorFactory
from .registry import AdaptorRegistry

# Make these components available when importing from the package
__all__ = [
    'interfaces',
    'AdaptorFactory',
    'AdaptorRegistry',
]