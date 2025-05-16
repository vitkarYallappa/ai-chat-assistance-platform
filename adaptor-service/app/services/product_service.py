import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal

from app.domain.models.product import Product
from app.core.exceptions import ProductNotFoundError, AdapterError

logger = logging.getLogger(__name__)

class ProductService:
    """Manages product domain logic."""
    
    def __init__(self, adapter_registry):
        """Initialize with adapter registry."""
        self.adapter_registry = adapter_registry
        
    async def get_products(
        self, 
        tenant_id: str,
        limit: int = 50, 
        offset: int = 0,
        category_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        sort_by: str = "name",
        sort_order: str = "asc"
    ) -> List[Product]:
        """Gets products using adaptors with filtering, sorting and pagination."""
        logger.info(
            f"Getting products for tenant {tenant_id} with filters: category_id={category_id}, "
            f"is_active={is_active}, price_range=[{min_price}-{max_price}], "
            f"sort={sort_by}:{sort_order}, pagination=[{offset}-{offset+limit}]"
        )
        
        try:
            # Get the appropriate adapter for the tenant
            adapter = self.adapter_registry.get_adapter(tenant_id, "product")
            
            # Get raw product data from the adapter
            product_data = await adapter.fetch_products(
                limit=limit,
                offset=offset,
                category_id=category_id,
                is_active=is_active,
                min_price=min_price,
                max_price=max_price,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            # Transform raw data to domain models
            products = [self._map_to_product_model(item) for item in product_data]
            
            logger.debug(f"Retrieved {len(products)} products for tenant {tenant_id}")
            return products
            
        except Exception as e:
            logger.error(f"Error fetching products for tenant {tenant_id}: {str(e)}")
            raise AdapterError(f"Failed to fetch products: {str(e)}")
    
    async def get_product_by_id(self, tenant_id: str, product_id: str) -> Product:
        """Gets product by ID."""
        logger.info(f"Getting product {product_id} for tenant {tenant_id}")
        
        try:
            # Get the appropriate adapter for the tenant
            adapter = self.adapter_registry.get_adapter(tenant_id, "product")
            
            # Get raw product data from the adapter
            product_data = await adapter.fetch_product_by_id(product_id)
            
            if not product_data:
                logger.warning(f"Product {product_id} not found for tenant {tenant_id}")
                raise ProductNotFoundError(f"Product with ID {product_id} not found")
            
            # Transform raw data to domain model
            product = self._map_to_product_model(product_data)
            
            logger.debug(f"Retrieved product {product_id} for tenant {tenant_id}")
            return product
            
        except ProductNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error fetching product {product_id} for tenant {tenant_id}: {str(e)}")
            raise AdapterError(f"Failed to fetch product: {str(e)}")
    
    async def search_products(
        self, 
        tenant_id: str, 
        search_term: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Product]:
        """Searches products by term."""
        logger.info(f"Searching products with term '{search_term}' for tenant {tenant_id}")
        
        try:
            adapter = self.adapter_registry.get_adapter(tenant_id, "product")
            product_data = await adapter.search_products(
                search_term=search_term,
                limit=limit,
                offset=offset
            )
            
            products = [self._map_to_product_model(item) for item in product_data]
            logger.debug(f"Found {len(products)} products matching '{search_term}'")
            return products
            
        except Exception as e:
            logger.error(f"Error searching products: {str(e)}")
            raise AdapterError(f"Failed to search products: {str(e)}")
    
    def format_product_data(self, product: Product) -> Dict[str, Any]:
        """Formats product for response."""
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": {
                "base": str(product.base_price),
                "sale": str(product.sale_price) if product.sale_price else None,
                "current": str(product.get_sale_price() or product.base_price)
            },
            "is_on_sale": product.is_on_sale(),
            "variations": product.variations,
            "attributes": product.attributes,
            "category_ids": product.category_ids,
            "is_active": product.is_active,
            "is_available": product.is_available(),
            "sku": product.sku,
            "image_urls": product.image_urls,
            "stock_quantity": product.stock_quantity
        }
    
    async def merge_product_data(self, tenant_id: str, product_id: str) -> Product:
        """Merges data from multiple sources for a complete product view."""
        logger.info(f"Merging product data for {product_id} from multiple sources")
        
        try:
            # Get core product data
            product = await self.get_product_by_id(tenant_id, product_id)
            
            # Get additional adapters if available
            inventory_adapter = self.adapter_registry.get_adapter(
                tenant_id, "inventory", required=False
            )
            
            # Merge inventory data if available
            if inventory_adapter:
                try:
                    inventory_data = await inventory_adapter.fetch_inventory_by_product(product_id)
                    if inventory_data:
                        product.stock_quantity = inventory_data.get("quantity")
                except Exception as e:
                    logger.warning(f"Failed to fetch inventory data: {str(e)}")
            
            return product
            
        except Exception as e:
            logger.error(f"Error merging product data: {str(e)}")
            raise AdapterError(f"Failed to merge product data: {str(e)}")
    
    def _map_to_product_model(self, data: Dict[str, Any]) -> Product:
        """Maps raw data to Product domain model."""
        # Convert string prices to Decimal
        base_price = Decimal(str(data.get("base_price", "0")))
        sale_price = Decimal(str(data.get("sale_price"))) if data.get("sale_price") else None
        
        return Product(
            id=data.get("id"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            base_price=base_price,
            sale_price=sale_price,
            sale_start_date=data.get("sale_start_date"),
            sale_end_date=data.get("sale_end_date"),
            variations=data.get("variations", []),
            attributes=data.get("attributes", {}),
            category_ids=data.get("category_ids", []),
            is_active=data.get("is_active", True),
            sku=data.get("sku"),
            image_urls=data.get("image_urls", []),
            stock_quantity=data.get("stock_quantity")
        )