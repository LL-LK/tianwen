"""
WebSocket heartbeat handling for Hermes-AGI
"""
import asyncio
import json
import logging
from typing import Callable, Awaitable

logger = logging.getLogger("hermes_agi")


class HeartbeatHandler:
    """心跳处理器"""
    
    def __init__(self, ws_manager, interval: int = 30, timeout: int = 60):
        self.ws_manager = ws_manager
        self.interval = interval
        self.timeout = timeout
        self._handlers: list = []
    
    def register_handler(self, handler: Callable[[str], Awaitable[None]]):
        """注册心跳事件处理器"""
        self._handlers.append(handler)
    
    async def handle_pong(self, client_id: str):
        """处理客户端pong响应"""
        self.ws_manager.update_heartbeat(client_id)
        
        # 调用注册的处理器
        for handler in self._handlers:
            try:
                await handler(client_id)
            except Exception as e:
                logger.error(f"[Heartbeat] Handler error for {client_id}: {e}")
    
    async def check_client_health(self, client_id: str) -> bool:
        """检查客户端健康状态"""
        import time
        if client_id not in self.ws_manager.clients:
            return False
        
        client = self.ws_manager.clients[client_id]
        time_since_heartbeat = time.time() - client.last_heartbeat
        
        if time_since_heartbeat > self.timeout:
            logger.warning(f"[Heartbeat] Client {client_id} health check failed: no heartbeat for {time_since_heartbeat:.1f}s")
            return False
        
        return True


class HeartbeatTask:
    """心跳任务"""
    
    def __init__(self, ws_manager, client_id: str, interval: int = 30):
        self.ws_manager = ws_manager
        self.client_id = client_id
        self.interval = interval
        self._task: asyncio.Task = None
        self._running = False
    
    async def start(self):
        """启动心跳任务"""
        self._running = True
        self._task = asyncio.create_task(self._run())
    
    async def stop(self):
        """停止心跳任务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _run(self):
        """心跳任务主循环"""
        while self._running:
            await asyncio.sleep(self.interval)
            
            if self.client_id not in self.ws_manager.clients:
                break
            
            try:
                await self.ws_manager.clients[self.client_id].websocket.send(
                    json.dumps({"type": "ping", "data": {}})
                )
            except Exception as e:
                logger.error(f"[Heartbeat] Failed to ping {self.client_id}: {e}")
                await self.ws_manager.disconnect(self.client_id)
                break


# Global heartbeat handler
heartbeat_handler = HeartbeatHandler(None)  # Will be initialized with ws_manager in main.py
