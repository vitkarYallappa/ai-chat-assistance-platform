"""
Interfaces package containing abstract base classes that define contracts
for various system components. These interfaces enable loose coupling and
dependency injection throughout the application.
"""

# Import interfaces
from app.domain.interfaces.model_interface import ModelInterface
from app.domain.interfaces.repository_interface import RepositoryInterface

# Export all interfaces for easier importing
__all__ = [
    "ModelInterface",
    "RepositoryInterface"
]