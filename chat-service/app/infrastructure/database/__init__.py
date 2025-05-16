"""
Database configuration and connection management.

This package provides database connection management, including connection
pooling, transaction support, and health monitoring.
"""

from app.infrastructure.database.connection import DatabaseConnection

__all__ = ['DatabaseConnection']