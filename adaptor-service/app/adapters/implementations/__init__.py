"""
Adapter implementations package for various external API integrations.
This package contains concrete implementations for different domains and platforms.
"""

# Import domain-specific implementations
from app.adapters.implementations.ecommerce import (
    ShopifyAdaptor,
    ShopifyConnector,
    ShopifyNormalizer,
    PLATFORM_SHOPIFY,
    PLATFORM_WOOCOMMERCE,
    PLATFORM_AMAZON
)

# Define domain constants
DOMAIN_ECOMMERCE = "ecommerce"
DOMAIN_HR = "hr"
DOMAIN_PHARMACY = "pharmacy"
DOMAIN_EDUCATION = "education"

# Mapping of adaptor types to their implementation classes
# This provides a convenient way to lookup implementations
ADAPTOR_IMPLEMENTATIONS = {
    f"{DOMAIN_ECOMMERCE}.{PLATFORM_SHOPIFY}": ShopifyAdaptor,
    # Add more implementations as they become available:
    # f"{DOMAIN_ECOMMERCE}.{PLATFORM_WOOCOMMERCE}": WooCommerceAdaptor,
    # f"{DOMAIN_HR}.workday": WorkdayAdaptor,
    # etc.
}

# Export all for easier importing elsewhere
__all__ = [
    # Adaptor implementation classes
    "ShopifyAdaptor",
    "ShopifyConnector",
    "ShopifyNormalizer",
    
    # Domain constants
    "DOMAIN_ECOMMERCE",
    "DOMAIN_HR",
    "DOMAIN_PHARMACY",
    "DOMAIN_EDUCATION",
    
    # Platform constants
    "PLATFORM_SHOPIFY",
    "PLATFORM_WOOCOMMERCE",
    "PLATFORM_AMAZON",
    
    # Implementation mappings
    "ADAPTOR_IMPLEMENTATIONS"
]