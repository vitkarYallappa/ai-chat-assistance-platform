from fastapi import Depends, HTTPException, Request, status
from typing import Optional

from app.config import get_settings, Settings
from app.channels.channel_factory import ChannelFactory
from app.domain.services.message_service import MessageService
from app.infrastructure.repositories.tenant_repository import TenantRepository
from app.domain.models.tenant import Tenant

# Configuration dependency
def get_settings_dependency() -> Settings:
    """
    Dependency to provide application settings.
    """
    return get_settings()

# Channel factory dependency
def get_channel_factory(settings: Settings = Depends(get_settings_dependency)) -> ChannelFactory:
    """
    Dependency to provide channel factory instance.
    """
    return ChannelFactory(settings)

# Tenant repository dependency
def get_tenant_repository(settings: Settings = Depends(get_settings_dependency)) -> TenantRepository:
    """
    Dependency to provide tenant repository instance.
    """
    return TenantRepository(settings.database.URI)

# Message service dependency
def get_message_service(
    channel_factory: ChannelFactory = Depends(get_channel_factory),
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
    settings: Settings = Depends(get_settings_dependency)
) -> MessageService:
    """
    Dependency to provide message service instance.
    """
    return MessageService(channel_factory, tenant_repository, settings)

# Current tenant dependency
async def get_current_tenant(
    request: Request,
    tenant_repository: TenantRepository = Depends(get_tenant_repository)
) -> Tenant:
    """
    Extracts and validates the current tenant from request.
    
    Requires tenant_context_middleware to be active.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant ID not provided or invalid"
        )
    
    tenant = await tenant_repository.get_by_id(tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found"
        )
    
    return tenant

# Correlation ID dependency
def get_correlation_id(request: Request) -> str:
    """
    Extracts the correlation ID from request state.
    
    Requires correlation_id_middleware to be active.
    """
    return getattr(request.state, "correlation_id", "unknown")

# Connection manager dependency
def get_connection_manager(request: Request):
    """
    Provides the connection manager instance from app state.
    """
    return request.app.state.connection_manager