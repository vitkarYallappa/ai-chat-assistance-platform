from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal


@dataclass
class Product:
    """Domain model for product data."""
    
    id: str
    name: str
    description: str
    base_price: Decimal
    sale_price: Optional[Decimal] = None
    sale_start_date: Optional[datetime] = None
    sale_end_date: Optional[datetime] = None
    variations: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    category_ids: List[str] = field(default_factory=list)
    is_active: bool = True
    sku: Optional[str] = None
    image_urls: List[str] = field(default_factory=list)
    stock_quantity: Optional[int] = None
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        base_price: Decimal,
        sale_price: Optional[Decimal] = None,
        sale_start_date: Optional[datetime] = None,
        sale_end_date: Optional[datetime] = None,
        variations: Optional[List[Dict[str, Any]]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        category_ids: Optional[List[str]] = None,
        is_active: bool = True,
        sku: Optional[str] = None,
        image_urls: Optional[List[str]] = None,
        stock_quantity: Optional[int] = None,
    ):
        """Initialize product with attributes."""
        self.id = id
        self.name = name
        self.description = description
        self.base_price = base_price
        self.sale_price = sale_price
        self.sale_start_date = sale_start_date
        self.sale_end_date = sale_end_date
        self.variations = variations or []
        self.attributes = attributes or {}
        self.category_ids = category_ids or []
        self.is_active = is_active
        self.sku = sku
        self.image_urls = image_urls or []
        self.stock_quantity = stock_quantity
    
    def has_variations(self) -> bool:
        """Checks if product has variations."""
        return len(self.variations) > 0
    
    def get_base_price(self) -> Decimal:
        """Gets base price."""
        return self.base_price
    
    def get_sale_price(self) -> Optional[Decimal]:
        """Gets sale price if applicable."""
        if not self.is_on_sale():
            return None
        return self.sale_price
    
    def is_on_sale(self) -> bool:
        """Determines if the product is currently on sale."""
        if not self.sale_price:
            return False
            
        now = datetime.now()
        
        # If no date range is set, but sale price exists, it's on sale
        if not self.sale_start_date and not self.sale_end_date:
            return True
            
        # Check if current time is within sale date range
        if self.sale_start_date and self.sale_end_date:
            return self.sale_start_date <= now <= self.sale_end_date
            
        # Check if after start date (no end date)
        if self.sale_start_date and not self.sale_end_date:
            return self.sale_start_date <= now
            
        # Check if before end date (no start date)
        if not self.sale_start_date and self.sale_end_date:
            return now <= self.sale_end_date
            
        return False
    
    def is_available(self) -> bool:
        """Checks if product is available."""
        if not self.is_active:
            return False
            
        # If we don't track stock, consider available
        if self.stock_quantity is None:
            return True
            
        return self.stock_quantity > 0