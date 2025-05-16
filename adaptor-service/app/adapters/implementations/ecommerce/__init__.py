"""
E-commerce adapters package for integrating with various e-commerce platforms.
Exports adapter classes for each supported e-commerce platform.
"""

from app.adapters.implementations.ecommerce.shopify import (
    ShopifyAdaptor,
    ShopifyConnector,
    ShopifyNormalizer
)

# Define platform identifier constants
PLATFORM_SHOPIFY = "shopify"
PLATFORM_WOOCOMMERCE = "woocommerce"
PLATFORM_AMAZON = "amazon"

# Export all for easier importing elsewhere
__all__ = [
    # Adaptor classes
    "ShopifyAdaptor",
    "ShopifyConnector", 
    "ShopifyNormalizer",
    
    # Platform identifiers
    "PLATFORM_SHOPIFY",
    "PLATFORM_WOOCOMMERCE",
    "PLATFORM_AMAZON"
]