from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, HTTPException

from app.services.inventory_service import InventoryService
from app.domain.schemas.responses import InventoryResponse, InventoryListResponse
from app.api.dependencies import get_inventory_service, get_tenant_id
from app.core.exceptions import ProductNotFoundError, AdapterError

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.get(
    "/",
    response_model=InventoryListResponse
)
async def get_inventory(
    tenant_id: str = Depends(get_tenant_id),
    inventory_service: InventoryService = Depends(get_inventory_service),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    location_id: Optional[str] = Query(None),
    updated_since: Optional[str] = Query(None)
):
    """Gets inventory filtered by criteria."""
    try:
        inventory_items = await inventory_service.get_inventory(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
            location_id=location_id,
            updated_since=updated_since
        )
        
        inventory_data = [
            await inventory_service.format_inventory_data(item) 
            for item in inventory_items
        ]
        
        return {
            "data": inventory_data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(inventory_data)
            }
        }
    
    except AdapterError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get(
    "/product/{product_id}",
    response_model=InventoryResponse
)
async def get_inventory_by_product(
    product_id: str = Path(...),
    tenant_id: str = Depends(get_tenant_id),
    inventory_service: InventoryService = Depends(get_inventory_service),
    location_id: Optional[str] = Query(None)
):
    """Gets inventory for product."""
    try:
        inventory = await inventory_service.get_inventory_by_product(
            tenant_id=tenant_id,
            product_id=product_id,
            location_id=location_id
        )
        
        inventory_data = await inventory_service.format_inventory_data(inventory)
        return {"data": inventory_data}
    
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AdapterError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get(
    "/low-stock",
    response_model=InventoryListResponse
)
async def get_low_stock_items(
    tenant_id: str = Depends(get_tenant_id),
    inventory_service: InventoryService = Depends(get_inventory_service),
    threshold: int = Query(10, ge=0),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    location_id: Optional[str] = Query(None)
):
    """Gets items with low stock."""
    try:
        low_stock_items = await inventory_service.get_low_stock_items(
            tenant_id=tenant_id,
            threshold=threshold,
            limit=limit,
            offset=offset,
            location_id=location_id
        )
        
        inventory_data = [
            await inventory_service.format_inventory_data(item) 
            for item in low_stock_items
        ]
        
        return {
            "data": inventory_data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(inventory_data)
            }
        }
    
    except AdapterError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get(
    "/availability/{product_id}"
)
async def check_availability(
    product_id: str = Path(...),
    tenant_id: str = Depends(get_tenant_id),
    inventory_service: InventoryService = Depends(get_inventory_service),
    quantity: int = Query(1, ge=1),
    location_id: Optional[str] = Query(None)
):
    """Checks product availability."""
    try:
        is_available = await inventory_service.check_availability(
            tenant_id=tenant_id,
            product_id=product_id,
            quantity=quantity,
            location_id=location_id
        )
        
        return {
            "product_id": product_id,
            "quantity_requested": quantity,
            "location_id": location_id,
            "is_available": is_available
        }
    
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AdapterError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get(
    "/stock-levels"
)
async def get_stock_levels(
    tenant_id: str = Depends(get_tenant_id),
    inventory_service: InventoryService = Depends(get_inventory_service),
    location_id: Optional[str] = Query(None)
):
    """Gets current stock levels."""
    try:
        stock_levels = await inventory_service.get_stock_levels(
            tenant_id=tenant_id,
            location_id=location_id
        )
        
        return {
            "data": stock_levels,
            "timestamp": stock_levels.get("timestamp")
        }
    
    except AdapterError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")