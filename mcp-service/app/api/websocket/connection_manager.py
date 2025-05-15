from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Any
import logging
import asyncio
import time
import uuid
from datetime import datetime

class ConnectionInfo:
    """
    Stores information about a WebSocket connection.
    """
    def __init__(
        self,
        websocket: WebSocket,
        tenant_id: str,
        user_id: str,
        client_id: str,
        connected_at: datetime = None
    ):
        self.websocket = websocket
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.client_id = client_id
        self.connected_at = connected_at or datetime.now()
        self.last_activity_at = self.connected_at
        self.is_alive = True
        self.metadata = {}
    
    def update_activity(self):
        """
        Updates the last activity timestamp.
        """
        self.last_activity_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converts connection info to dictionary (excluding websocket).
        """
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "client_id": self.client_id,
            "connected_at": self.connected_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "is_alive": self.is_alive,
            "metadata": self.metadata
        }

class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication.
    
    The connection manager maintains a registry of active WebSocket connections
    organized by tenant, user, and client to enable targeted message delivery.
    """
    def __init__(self):
        # Active connections organized as tenant_id -> user_id -> client_id -> ConnectionInfo
        self.active_connections: Dict[str, Dict[str, Dict[str, ConnectionInfo]]] = {}
        
        # Start background tasks
        self.background_tasks = set()
        self.start_background_tasks()
    
    def start_background_tasks(self):
        """
        Starts background tasks for connection management.
        """
        heartbeat_task = asyncio.create_task(self._heartbeat_task())
        cleanup_task = asyncio.create_task(self._cleanup_task())
        
        # Keep reference to tasks to prevent garbage collection
        self.background_tasks.add(heartbeat_task)
        self.background_tasks.add(cleanup_task)
        
        # Remove task from set when done
        heartbeat_task.add_done_callback(self.background_tasks.discard)
        cleanup_task.add_done_callback(self.background_tasks.discard)
    
    async def connect(
        self,
        websocket: WebSocket,
        tenant_id: str,
        user_id: str,
        client_id: Optional[str] = None
    ) -> str:
        """
        Registers a new WebSocket connection.
        
        Returns the client_id for the connection.
        """
        # Generate client_id if not provided
        if not client_id:
            client_id = str(uuid.uuid4())
        
        # Initialize tenant dict if not exists
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = {}
        
        # Initialize user dict if not exists
        if user_id not in self.active_connections[tenant_id]:
            self.active_connections[tenant_id][user_id] = {}
        
        # Accept the connection
        await websocket.accept()
        
        # Store connection info
        connection_info = ConnectionInfo(
            websocket=websocket,
            tenant_id=tenant_id,
            user_id=user_id,
            client_id=client_id
        )
        
        self.active_connections[tenant_id][user_id][client_id] = connection_info
        
        logging.info(
            f"WebSocket connected for tenant {tenant_id}, user {user_id}, client {client_id}",
            extra={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "client_id": client_id
            }
        )
        
        return client_id
    
    async def disconnect(
        self,
        tenant_id: str,
        user_id: str,
        client_id: str
    ) -> None:
        """
        Removes a WebSocket connection.
        """
        if (
            tenant_id in self.active_connections and
            user_id in self.active_connections[tenant_id] and
            client_id in self.active_connections[tenant_id][user_id]
        ):
            # Get connection info
            connection_info = self.active_connections[tenant_id][user_id][client_id]
            
            # Remove connection
            del self.active_connections[tenant_id][user_id][client_id]
            
            # Cleanup empty dictionaries
            if not self.active_connections[tenant_id][user_id]:
                del self.active_connections[tenant_id][user_id]
            
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]
            
            logging.info(
                f"WebSocket disconnected for tenant {tenant_id}, user {user_id}, client {client_id}",
                extra={
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "client_id": client_id
                }
            )
            
            # Close WebSocket if still open
            try:
                await connection_info.websocket.close()
            except Exception:
                pass
    
    async def send_message(
        self,
        tenant_id: str,
        user_id: str,
        client_id: str,
        message: Any
    ) -> bool:
        """
        Sends a message to a specific WebSocket connection.
        
        Returns True if the message was sent successfully, False otherwise.
        """
        if (
            tenant_id in self.active_connections and
            user_id in self.active_connections[tenant_id] and
            client_id in self.active_connections[tenant_id][user_id]
        ):
            connection_info = self.active_connections[tenant_id][user_id][client_id]
            
            try:
                # Send message
                await connection_info.websocket.send_json(message)
                
                # Update activity timestamp
                connection_info.update_activity()
                
                return True
            except WebSocketDisconnect:
                # Handle disconnection
                await self.disconnect(tenant_id, user_id, client_id)
            except Exception as e:
                logging.error(
                    f"Error sending message to WebSocket: {str(e)}",
                    extra={
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "client_id": client_id
                    },
                    exc_info=True
                )
        
        return False
    
    async def broadcast_to_user(
        self,
        tenant_id: str,
        user_id: str,
        message: Any
    ) -> int:
        """
        Broadcasts a message to all connections for a specific user.
        
        Returns the number of connections that received the message.
        """
        sent_count = 0
        
        if (
            tenant_id in self.active_connections and
            user_id in self.active_connections[tenant_id]
        ):
            # Get all clients for the user
            clients = list(self.active_connections[tenant_id][user_id].keys())
            
            # Send message to each client
            for client_id in clients:
                success = await self.send_message(tenant_id, user_id, client_id, message)
                if success:
                    sent_count += 1
        
        return sent_count
    
    async def broadcast_to_tenant(
        self,
        tenant_id: str,
        message: Any
    ) -> int:
        """
        Broadcasts a message to all connections for a specific tenant.
        
        Returns the number of connections that received the message.
        """
        sent_count = 0
        
        if tenant_id in self.active_connections:
            # Get all users for the tenant
            users = list(self.active_connections[tenant_id].keys())
            
            # Send message to each user
            for user_id in users:
                sent_count += await self.broadcast_to_user(tenant_id, user_id, message)
        
        return sent_count
    
    async def broadcast(
        self,
        message: Any
    ) -> int:
        """
        Broadcasts a message to all connections.
        
        Returns the number of connections that received the message.
        """
        sent_count = 0
        
        # Get all tenants
        tenants = list(self.active_connections.keys())
        
        # Send message to each tenant
        for tenant_id in tenants:
            sent_count += await self.broadcast_to_tenant(tenant_id, message)
        
        return sent_count
    
    def get_connection_count(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> int:
        """
        Returns the number of active connections.
        
        Can be filtered by tenant and/or user.
        """
        if tenant_id is None:
            # Count all connections
            return sum(
                sum(
                    len(clients)
                    for clients in users.values()
                )
                for users in self.active_connections.values()
            )
        elif user_id is None:
            # Count connections for a specific tenant
            if tenant_id not in self.active_connections:
                return 0
            
            return sum(
                len(clients)
                for clients in self.active_connections[tenant_id].values()
            )
        else:
            # Count connections for a specific tenant and user
            if (
                tenant_id not in self.active_connections or
                user_id not in self.active_connections[tenant_id]
            ):
                return 0
            
            return len(self.active_connections[tenant_id][user_id])
    
    def get_connection_info(
        self,
        tenant_id: str,
        user_id: str,
        client_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Returns information about a specific connection.
        """
        if (
            tenant_id in self.active_connections and
            user_id in self.active_connections[tenant_id] and
            client_id in self.active_connections[tenant_id][user_id]
        ):
            connection_info = self.active_connections[tenant_id][user_id][client_id]
            return connection_info.to_dict()
        
        return None
    
    async def _heartbeat_task(self) -> None:
        """
        Background task to send heartbeat messages to all connections.
        
        This helps keep connections alive and detect stale connections.
        """
        while True:
            try:
                # Send heartbeat every 30 seconds
                await asyncio.sleep(30)
                
                # Get current timestamp
                timestamp = int(time.time())
                
                # Heartbeat message
                heartbeat_message = {
                    "type": "heartbeat",
                    "timestamp": timestamp
                }
                
                # Send heartbeat to all connections
                await self.broadcast(heartbeat_message)
                
                logging.debug(f"Sent heartbeat to {self.get_connection_count()} connections")
            except Exception as e:
                logging.error(f"Error in heartbeat task: {str(e)}", exc_info=True)
    
    async def _cleanup_task(self) -> None:
        """
        Background task to clean up stale connections.
        
        Removes connections that haven't had activity for more than 5 minutes.
        """
        while True:
            try:
                # Run cleanup every 5 minutes
                await asyncio.sleep(300)  # 5 minutes
                
                # Get current timestamp
                now = datetime.now()
                
                # Find stale connections
                stale_connections = []
                
                for tenant_id, users in self.active_connections.items():
                    for user_id, clients in users.items():
                        for client_id, connection_info in clients.items():
                            # Check if connection is stale (inactive for more than 5 minutes)
                            time_since_activity = (now - connection_info.last_activity_at).total_seconds()
                            
                            if time_since_activity > 300:  # 5 minutes
                                stale_connections.append((tenant_id, user_id, client_id))
                
                # Disconnect stale connections
                for tenant_id, user_id, client_id in stale_connections:
                    logging.info(
                        f"Cleaning up stale connection for tenant {tenant_id}, user {user_id}, client {client_id}",
                        extra={
                            "tenant_id": tenant_id,
                            "user_id": user_id,
                            "client_id": client_id
                        }
                    )
                    
                    await self.disconnect(tenant_id, user_id, client_id)
                
                if stale_connections:
                    logging.info(f"Cleaned up {len(stale_connections)} stale connections")
            except Exception as e:
                logging.error(f"Error in cleanup task: {str(e)}", exc_info=True)