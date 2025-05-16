"""
Message Normalizers Package.

This package contains normalizers for converting channel-specific message formats
to/from the standardized internal format used throughout the system.
"""

from app.normalizers.base import BaseNormalizer
from app.normalizers.text import TextNormalizer
from app.normalizers.image import ImageNormalizer
from app.normalizers.interactive import InteractiveNormalizer

# Dictionary mapping message types to their normalizer classes
# This can be extended as more normalizers are added
NORMALIZER_MAP = {
    "text": TextNormalizer,
    "image": ImageNormalizer,
    "interactive": InteractiveNormalizer,
}

__all__ = [
    "BaseNormalizer",
    "TextNormalizer",
    "ImageNormalizer",
    "InteractiveNormalizer",
    "NORMALIZER_MAP",
    "get_normalizer_for_type",
    "get_normalizer_for_message"
]
