"""
MongoDB client implementation.

This package provides MongoDB-specific connection management and utilities,
including connection pooling, indexing, and transaction support.
"""

from app.infrastructure.database.mongodb.client import MongoDBClient

__all__ = ['MongoDBClient']