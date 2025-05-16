from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, Path, HTTPException

from app.services.product_service import ProductService
from app.domain.schemas.requests import SearchProductsRequest
from app.domain.schemas.responses import ProductResponse, ProductListResponse
from app.api.dependencies import get_product_service, get_tenant_id
from app.core.exceptions import ProductNotFoundError, AdapterError

router = APIRouter(prefix="/products", tags=["products"])

@router.get(
    "/",
    response_model=ProductListResponse,
    summary="Get products"
)
async def get_products(
    tenant_id: str = Depends(get_tenant_id),
    product_service: ProductService = Depends(get_product_service),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc")
):
    """Gets products filtered by criteria."""
    try:
        # Convert float prices to Decimal
        min_price_decimal = Decimal(str(min_price)) if min_price is not None else None
        max_price_decimal = Decimal(str(max_price)) if max_price is not None else None
        
        products = await product_service.get_products(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
            category_id=category_id,
            is_active=is_active,
            min_price=min_price_decimal,
            max_price=max_price_decimal,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Format products for response
        product_data = [product_service.format_product_data(product) for product in products]
        
        return {
            "data": product_data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(product_data)
            }
        }
    
    except AdapterError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get(
    "/{product_id}",
    response_model=ProductResponse
)
async def get_product_by_id(
    product_id: str = Path(...),
    tenant_id: str = Depends(get_tenant_id),
    product_service: ProductService = Depends(get_product_service)
):
    """Gets product by ID."""
    try:
        product = await product_service.merge_product_data(tenant_id, product_id)
        return {"data": product_service.format_product_data(product)}
    
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AdapterError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get(
    "/{product_id}/variations",
    response_model=ProductListResponse
)
async def get_product_variations(
    product_id: str = Path(...),
    tenant_id: str = Depends(get_tenant_id),
    product_service: ProductService = Depends(get_product_service)
):
    """Gets product variations."""
    try:
        parent_product = await product_service.get_product_by_id(tenant_id, product_id)
        
        if not parent_product.has_variations():
            return {"data": [], "pagination": {"limit": 0, "offset": 0, "total": 0}}
        
        variation_ids = [v.get("id") for v in parent_product.variations if "id" in v]
        variations = []
        
        for var_id in variation_ids:
            try:
                var_product = await product_service.get_product_by_id(tenant_id, var_id)
                variations.append(var_product)
            except ProductNotFoundError:
                continue
        
        variation_data = [product_service.format_product_data(v) for v in variations]
        
        return {
            "data": variation_data,
            "pagination": {
                "limit": len(variation_data),
                "offset": 0,
                "total": len(variation_data)
            }
        }
    
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AdapterError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post(
    "/search",
    response_model=ProductListResponse
)
async def search_products(
    request: SearchProductsRequest,
    tenant_id: str = Depends(get_tenant_id),
    product_service: ProductService = Depends(get_product_service)
):
    """Searches products by term."""
    try:
        products = await product_service.search_products(
            tenant_id=tenant_id,
            search_term=request.search_term,
            limit=request.limit,
            offset=request.offset
        )
        
        product_data = [product_service.format_product_data(product) for product in products]
        
        return {
            "data": product_data,
            "pagination": {
                "limit": request.limit,
                "offset": request.offset,
                "total": len(product_data)
            }
        }
    
    except AdapterError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get(
    "/category/{category_id}",
    response_model=ProductListResponse
)
async def get_products_by_category(
    category_id: str = Path(...),
    tenant_id: str = Depends(get_tenant_id),
    product_service: ProductService = Depends(get_product_service),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc")
):
    """Gets products by category."""
    try:
        products = await product_service.get_products(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
            category_id=category_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        product_data = [product_service.format_product_data(product) for product in products]
        
        return {
            "data": product_data,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(product_data)
            }
        }
    
    except AdapterError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")