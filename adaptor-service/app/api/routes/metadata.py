from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel
from typing import Dict, List, Optional

from app.api.dependencies import get_adaptor_factory, get_current_tenant
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

# Initialize router and logger
metadata_router = APIRouter()
logger = get_logger(__name__)


class AdaptorCapability(BaseModel):
    """Model for adaptor capability metadata."""
    name: str
    description: str
    supported_operations: List[str]
    schema_version: str


class AdaptorInfo(BaseModel):
    """Model for basic adaptor information."""
    id: str
    name: str
    type: str
    domain: str
    description: str
    version: str


class AdaptorDetailedInfo(AdaptorInfo):
    """Model for detailed adaptor information."""
    capabilities: List[AdaptorCapability]
    configuration_schema: Optional[Dict] = None


@metadata_router.get(
    "/adaptors",
    response_model=List[AdaptorInfo],
    status_code=status.HTTP_200_OK,
    summary="List available adaptors",
    description="Returns a list of available adaptor implementations."
)
async def get_adaptors(
    tenant_id: str = Depends(get_current_tenant),
    domain: Optional[str] = Query(None, description="Filter adaptors by domain"),
    type: Optional[str] = Query(None, description="Filter adaptors by type")
) -> List[AdaptorInfo]:
    """
    List available adaptor implementations with optional filtering.
    
    Args:
        tenant_id: Tenant ID from dependency
        domain: Optional domain filter
        type: Optional type filter
        
    Returns:
        List[AdaptorInfo]: List of adaptor information
    """
    logger.info(f"Listing adaptors for tenant: {tenant_id}")
    
    # This is a placeholder implementation
    # In the future, we'll query the adaptor registry for available adaptors
    
    adaptors = [
        AdaptorInfo(
            id="shopify",
            name="Shopify",
            type="ecommerce",
            domain="product",
            description="Adaptor for Shopify e-commerce platform",
            version="1.0.0"
        ),
        AdaptorInfo(
            id="woocommerce",
            name="WooCommerce",
            type="ecommerce",
            domain="product",
            description="Adaptor for WooCommerce WordPress plugin",
            version="1.0.0"
        ),
        AdaptorInfo(
            id="workday",
            name="Workday",
            type="hr",
            domain="employee",
            description="Adaptor for Workday HR platform",
            version="1.0.0"
        ),
        AdaptorInfo(
            id="epic",
            name="Epic",
            type="healthcare",
            domain="pharmacy",
            description="Adaptor for Epic healthcare systems",
            version="1.0.0"
        ),
        AdaptorInfo(
            id="canvas",
            name="Canvas",
            type="education",
            domain="lms",
            description="Adaptor for Canvas learning management system",
            version="1.0.0"
        )
    ]
    
    # Apply domain filter if provided
    if domain:
        adaptors = [a for a in adaptors if a.domain == domain]
    
    # Apply type filter if provided
    if type:
        adaptors = [a for a in adaptors if a.type == type]
    
    return adaptors


@metadata_router.get(
    "/adaptors/{adaptor_id}",
    response_model=AdaptorDetailedInfo,
    status_code=status.HTTP_200_OK,
    summary="Get adaptor capabilities",
    description="Returns detailed information about a specific adaptor implementation."
)
async def get_adaptor_capabilities(
    adaptor_id: str = Path(..., description="ID of the adaptor"),
    tenant_id: str = Depends(get_current_tenant),
    adaptor_factory: Dict = Depends(get_adaptor_factory)
) -> AdaptorDetailedInfo:
    """
    Get detailed information about a specific adaptor.
    
    Args:
        adaptor_id: The ID of the adaptor to retrieve
        tenant_id: Tenant ID from dependency
        adaptor_factory: Adaptor factory from dependency
        
    Returns:
        AdaptorDetailedInfo: Detailed adaptor information with capabilities
        
    Raises:
        NotFoundError: If the adaptor is not found
    """
    logger.info(f"Getting capabilities for adaptor {adaptor_id}, tenant: {tenant_id}")
    
    # This is a placeholder implementation
    # In the future, we'll query the adaptor registry for the specific adaptor
    
    # Mapping of adaptor ID to mock capabilities for demo purposes
    adaptor_capabilities = {
        "shopify": AdaptorDetailedInfo(
            id="shopify",
            name="Shopify",
            type="ecommerce",
            domain="product",
            description="Adaptor for Shopify e-commerce platform",
            version="1.0.0",
            capabilities=[
                AdaptorCapability(
                    name="product",
                    description="Product data access",
                    supported_operations=["get", "list", "search"],
                    schema_version="1.0.0"
                ),
                AdaptorCapability(
                    name="inventory",
                    description="Inventory data access",
                    supported_operations=["get", "list"],
                    schema_version="1.0.0"
                )
            ],
            configuration_schema={
                "type": "object",
                "required": ["api_key", "shop_name"],
                "properties": {
                    "api_key": {"type": "string"},
                    "shop_name": {"type": "string"},
                    "api_version": {"type": "string", "default": "2023-01"}
                }
            }
        ),
        "woocommerce": AdaptorDetailedInfo(
            id="woocommerce",
            name="WooCommerce",
            type="ecommerce",
            domain="product",
            description="Adaptor for WooCommerce WordPress plugin",
            version="1.0.0",
            capabilities=[
                AdaptorCapability(
                    name="product",
                    description="Product data access",
                    supported_operations=["get", "list", "search"],
                    schema_version="1.0.0"
                ),
                AdaptorCapability(
                    name="inventory",
                    description="Inventory data access",
                    supported_operations=["get", "list"],
                    schema_version="1.0.0"
                )
            ],
            configuration_schema={
                "type": "object",
                "required": ["url", "consumer_key", "consumer_secret"],
                "properties": {
                    "url": {"type": "string"},
                    "consumer_key": {"type": "string"},
                    "consumer_secret": {"type": "string"},
                    "version": {"type": "string", "default": "wc/v3"}
                }
            }
        ),
        "workday": AdaptorDetailedInfo(
            id="workday",
            name="Workday",
            type="hr",
            domain="employee",
            description="Adaptor for Workday HR platform",
            version="1.0.0",
            capabilities=[
                AdaptorCapability(
                    name="employee",
                    description="Employee data access",
                    supported_operations=["get", "list", "search"],
                    schema_version="1.0.0"
                ),
                AdaptorCapability(
                    name="position",
                    description="Position data access",
                    supported_operations=["get", "list"],
                    schema_version="1.0.0"
                )
            ],
            configuration_schema={
                "type": "object",
                "required": ["tenant_url", "client_id", "client_secret"],
                "properties": {
                    "tenant_url": {"type": "string"},
                    "client_id": {"type": "string"},
                    "client_secret": {"type": "string"},
                    "api_version": {"type": "string", "default": "v1"}
                }
            }
        ),
        "epic": AdaptorDetailedInfo(
            id="epic",
            name="Epic",
            type="healthcare",
            domain="pharmacy",
            description="Adaptor for Epic healthcare systems",
            version="1.0.0",
            capabilities=[
                AdaptorCapability(
                    name="medication",
                    description="Medication data access",
                    supported_operations=["get", "list", "search"],
                    schema_version="1.0.0"
                ),
                AdaptorCapability(
                    name="patient",
                    description="Patient data access (anonymized)",
                    supported_operations=["get", "list"],
                    schema_version="1.0.0"
                )
            ],
            configuration_schema={
                "type": "object",
                "required": ["base_url", "client_id", "client_secret"],
                "properties": {
                    "base_url": {"type": "string"},
                    "client_id": {"type": "string"},
                    "client_secret": {"type": "string"},
                    "scope": {"type": "string", "default": "medication.read patient.read"}
                }
            }
        ),
        "canvas": AdaptorDetailedInfo(
            id="canvas",
            name="Canvas",
            type="education",
            domain="lms",
            description="Adaptor for Canvas learning management system",
            version="1.0.0",
            capabilities=[
                AdaptorCapability(
                    name="course",
                    description="Course data access",
                    supported_operations=["get", "list", "search"],
                    schema_version="1.0.0"
                ),
                AdaptorCapability(
                    name="assignment",
                    description="Assignment data access",
                    supported_operations=["get", "list"],
                    schema_version="1.0.0"
                )
            ],
            configuration_schema={
                "type": "object",
                "required": ["api_url", "access_token"],
                "properties": {
                    "api_url": {"type": "string"},
                    "access_token": {"type": "string"},
                    "per_page": {"type": "integer", "default": 50}
                }
            }
        )
    }
    
    # Check if adaptor exists
    if adaptor_id not in adaptor_capabilities:
        raise NotFoundError(resource_type="Adaptor", resource_id=adaptor_id)
    
    return adaptor_capabilities[adaptor_id]