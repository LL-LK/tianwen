"""
WebSocket client handling for Hermes-AGI
"""
import asyncio
import json
import logging
from typing import Optional

logger = logging.getLogger("hermes_agi")


class WebSocketMessageHandler:
    """WebSocket消息处理器"""
    
    def __init__(self, ws_manager):
        self.ws_manager = ws_manager
        self._message_handlers: dict = {}
    
    def register(self, event_type: str, handler):
        """注册消息处理器"""
        self._message_handlers[event_type] = handler
    
    async def handle_message(self, client_id: str, message: dict):
        """处理接收到的消息"""
        event_type = message.get("type")
        data = message.get("data", {})
        
        if event_type == "pong":
            # 处理心跳响应
            self.ws_manager.update_heartbeat(client_id)
            return
        
        handler = self._message_handlers.get(event_type)
        if handler:
            try:
                await handler(client_id, data)
            except Exception as e:
                logger.error(f"[WS] Message handler error for {event_type}: {e}")
        else:
            logger.debug(f"[WS] No handler for event type: {event_type}")


class ClientConnection:
    """客户端连接封装"""
    
    def __init__(self, ws_manager, client_id: str, websocket):
        self.ws_manager = ws_manager
        self.client_id = client_id
        self.websocket = websocket
        self._message_handler: Optional[WebSocketMessageHandler] = None
        self._closed = False
    
    def set_message_handler(self, handler: WebSocketMessageHandler):
        """设置消息处理器"""
        self._message_handler = handler
    
    async def send(self, event_type: str, data: dict):
        """发送消息到客户端"""
        if self._closed:
            return
        
        try:
            message = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
            await self.websocket.send(message)
        except Exception as e:
            logger.error(f"[WS] Send error to {self.client_id}: {e}")
            self._closed = True
    
    async def receive(self) -> Optional[dict]:
        """接收客户端消息"""
        if self._closed:
            return None
        
        try:
            data = await self.websocket.receive()
            text = data.get("text")
            if text:
                return json.loads(text)
        except Exception as e:
            logger.error(f"[WS] Receive error from {self.client_id}: {e}")
            self._closed = True
        
        return None
    
    async def close(self):
        """关闭连接"""
        self._closed = True
        await self.ws_manager.disconnect(self.client_id)


class ClientRegistry:
    """客户端注册表"""
    
    def __init__(self, ws_manager):
        self.ws_manager = ws_manager
        self._connections: dict = {}
        self._locks: dict = {}
    
    async def register(self, client_id: str, websocket) -> ClientConnection:
        """注册新客户端连接"""
        import asyncio
        if client_id not in self._locks:
            self._locks[client_id] = asyncio.Lock()
        
        async with self._locks[client_id]:
            connection = ClientConnection(self.ws_manager, client_id, websocket)
            self._connections[client_id] = connection
            return connection
    
    async def unregister(self, client_id: str):
        """注销客户端连接"""
        if client_id in self._connections:
            del self._connections[client_id]
        
        if client_id in self._locks:
            del self._locks[client_id]
    
    def get(self, client_id: str) -> Optional[ClientConnection]:
        """获取客户端连接"""
        return self._connections.get(client_id)
    
    async def broadcast_all(self, event_type: str, data: dict):
        """广播到所有连接"""
        for connection in self._connections.values():
            await connection.send(event_type, data)
    
    async def send_to(self, client_id: str, event_type: str, data: dict):
        """发送消息到指定客户端"""
        connection = self._connections.get(client_id)
        if connection:
            await connection.send(event_type, data)
