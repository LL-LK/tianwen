"""
WebSocket connection manager for Hermes-AGI
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Set, Optional
from quart import websocket

logger = logging.getLogger("hermes_agi")


@dataclass
class HeartbeatConfig:
    """心跳配置"""
    interval: int = 30  # 心跳间隔(秒)
    timeout: int = 60  # 超时时间(秒)


@dataclass
class WebSocketClient:
    """WebSocket客户端"""
    client_id: str
    websocket: websocket
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    last_heartbeat: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    subscribed_events: Set[str] = field(default_factory=set)


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self._clients: Dict[str, WebSocketClient] = {}
        self._subscriptions: Dict[str, Set[str]] = {}  # event_type -> set of client_ids
        self._heartbeat_config = HeartbeatConfig()
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}
    
    @property
    def clients(self) -> Dict[str, WebSocketClient]:
        return self._clients
    
    async def connect(self, client_id: str, ws: websocket, user_id: str = None, session_id: str = None) -> WebSocketClient:
        """注册新的WebSocket连接"""
        client = WebSocketClient(
            client_id=client_id,
            websocket=ws,
            user_id=user_id,
            session_id=session_id
        )
        self._clients[client_id] = client
        logger.info(f"[WS] Client connected: {client_id} (user={user_id}, session={session_id})")
        
        # 启动心跳检测
        self._heartbeat_tasks[client_id] = asyncio.create_task(
            self._heartbeat_loop(client_id)
        )
        
        return client
    
    async def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self._clients:
            # 取消心跳任务
            if client_id in self._heartbeat_tasks:
                self._heartbeat_tasks[client_id].cancel()
                del self._heartbeat_tasks[client_id]
            
            # 取消所有订阅
            client = self._clients[client_id]
            for event_type in client.subscribed_events:
                if event_type in self._subscriptions:
                    self._subscriptions[event_type].discard(client_id)
            
            del self._clients[client_id]
            logger.info(f"[WS] Client disconnected: {client_id}")
    
    async def send_to_client(self, client_id: str, event_type: str, data: dict):
        """向指定客户端发送消息"""
        if client_id not in self._clients:
            logger.warning(f"[WS] Cannot send to unknown client: {client_id}")
            return
        
        try:
            message = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
            await self._clients[client_id].websocket.send(message)
        except Exception as e:
            logger.error(f"[WS] Error sending to client {client_id}: {e}")
            await self.disconnect(client_id)
    
    async def broadcast(self, event_type: str, data: dict, event_filter: str = None):
        """广播消息到所有连接的客户端，或按事件类型筛选"""
        message = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
        
        target_clients = set()
        if event_filter:
            target_clients = self._subscriptions.get(event_filter, set())
        else:
            target_clients = set(self._clients.keys())
        
        disconnected = []
        for client_id in target_clients:
            if client_id in self._clients:
                try:
                    await self._clients[client_id].websocket.send(message)
                except Exception as e:
                    logger.error(f"[WS] Broadcast error to {client_id}: {e}")
                    disconnected.append(client_id)
        
        # 清理断开的客户端
        for client_id in disconnected:
            await self.disconnect(client_id)
    
    def subscribe(self, client_id: str, event_type: str):
        """订阅事件"""
        if client_id not in self._clients:
            return
        
        self._clients[client_id].subscribed_events.add(event_type)
        
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = set()
        self._subscriptions[event_type].add(client_id)
        logger.debug(f"[WS] Client {client_id} subscribed to {event_type}")
    
    def unsubscribe(self, client_id: str, event_type: str):
        """取消订阅事件"""
        if client_id in self._clients:
            self._clients[client_id].subscribed_events.discard(event_type)
        
        if event_type in self._subscriptions:
            self._subscriptions[event_type].discard(client_id)
    
    async def _heartbeat_loop(self, client_id: str):
        """心跳检测循环"""
        while True:
            await asyncio.sleep(self._heartbeat_config.interval)
            
            if client_id not in self._clients:
                break
            
            client = self._clients[client_id]
            now = asyncio.get_event_loop().time()
            time_since_last_heartbeat = now - client.last_heartbeat
            
            if time_since_last_heartbeat > self._heartbeat_config.timeout:
                logger.warning(f"[WS] Client {client_id} heartbeat timeout")
                await self.disconnect(client_id)
                break
            
            # 发送ping
            try:
                await client.websocket.send(json.dumps({"type": "ping", "data": {}}))
            except Exception as e:
                logger.error(f"[WS] Heartbeat ping failed for {client_id}: {e}")
                await self.disconnect(client_id)
                break
    
    def update_heartbeat(self, client_id: str):
        """更新客户端心跳时间戳"""
        if client_id in self._clients:
            self._clients[client_id].last_heartbeat = asyncio.get_event_loop().time()
    
    def get_client_info(self, client_id: str) -> Optional[dict]:
        """获取客户端信息"""
        if client_id not in self._clients:
            return None
        
        client = self._clients[client_id]
        return {
            "client_id": client.client_id,
            "user_id": client.user_id,
            "session_id": client.session_id,
            "subscribed_events": list(client.subscribed_events),
            "last_heartbeat": client.last_heartbeat
        }
    
    def list_clients(self) -> list:
        """列出所有客户端"""
        return [
            self.get_client_info(client_id)
            for client_id in self._clients.keys()
        ]


# Global WebSocket manager instance
ws_manager = WebSocketManager()
