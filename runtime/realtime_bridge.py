"""
天问-AGI 实时状态桥接模块
将 HermesAGI 内部状态实时映射到 WebSocket 推送通道

架构:
  HermesAGI (内部状态)
       │
       ▼
  AgentStateBridge  ── 状态采集、变换、节流
       │
       ▼
  EventBus  ── 发布/订阅事件总线
       │
       ▼
  WebSocketManager  ── 广播到所有连接客户端
"""

import asyncio
import json
import time
import logging
from typing import Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from collections import deque
from datetime import datetime
from threading import Lock

logger = logging.getLogger("hermes_agi.realtime_bridge")


@dataclass
class ObservatorySnapshot:
    timestamp: str = ""
    status: str = "idle"
    uptime_hours: float = 0.0
    discoveries: int = 0
    hypotheses: int = 0
    ws_clients: int = 0
    current_target: Optional[dict] = None
    queue: list = field(default_factory=list)
    devices: dict = field(default_factory=dict)
    research_loop: Optional[dict] = None
    detections: Optional[dict] = None
    latest_image: Optional[dict] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = d["timestamp"] or datetime.now().isoformat()
        return d


class EventBus:
    """轻量级发布/订阅事件总线"""

    def __init__(self, max_history: int = 200):
        self._subscribers: dict[str, list[Callable]] = {}
        self._history: dict[str, deque] = {}
        self._max_history = max_history
        self._lock = Lock()

    def subscribe(self, event_type: str, callback: Callable):
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    cb for cb in self._subscribers[event_type] if cb is not callback
                ]

    def publish(self, event_type: str, data: Any):
        with self._lock:
            if event_type not in self._history:
                self._history[event_type] = deque(maxlen=self._max_history)
            self._history[event_type].append({
                "timestamp": datetime.now().isoformat(),
                "data": data,
            })

        subscribers = self._subscribers.get(event_type, [])
        for cb in subscribers:
            try:
                cb(event_type, data)
            except Exception as e:
                logger.error(f"EventBus callback error for {event_type}: {e}")

    def get_history(self, event_type: str, limit: int = 50) -> list:
        with self._lock:
            history = list(self._history.get(event_type, []))
            return history[-limit:]

    def clear_history(self, event_type: str = None):
        with self._lock:
            if event_type:
                self._history.pop(event_type, None)
            else:
                self._history.clear()


class AgentStateBridge:
    """将 HermesAGI 内部状态桥接到观测站快照"""

    def __init__(self, event_bus: EventBus, throttle_ms: int = 500):
        self._event_bus = event_bus
        self._throttle_ms = throttle_ms
        self._last_snapshot_time = 0.0
        self._snapshot_lock = Lock()
        self._agent = None
        self._start_time = time.time()

        self._observatory_state = {
            "status": "idle",
            "discoveries": 0,
            "hypotheses": 0,
            "current_target": None,
            "queue": [],
            "devices": {},
            "research_loop": None,
            "detections": None,
            "latest_image": None,
        }

        self._alert_history: list = []
        self._log_history: list = []
        self._max_alerts = 200
        self._max_logs = 500

    def bind_agent(self, agent):
        """绑定 HermesAGI 实例"""
        self._agent = agent
        self._start_time = time.time()
        logger.info("AgentStateBridge bound to HermesAGI instance")

    def update_status(self, status: str):
        self._observatory_state["status"] = status
        self._add_log("SYSTEM", f"观测站状态变更: {status}")
        self._publish_snapshot()

    def update_target(self, target: dict):
        self._observatory_state["current_target"] = target
        self._publish_snapshot()

    def update_queue(self, queue: list):
        self._observatory_state["queue"] = queue
        self._event_bus.publish("queue_update", queue)
        self._publish_snapshot()

    def update_devices(self, devices: dict):
        self._observatory_state["devices"] = devices
        self._publish_snapshot()

    def update_research_loop(self, research: dict):
        self._observatory_state["research_loop"] = research
        self._publish_snapshot()

    def update_detections(self, detections: dict):
        self._observatory_state["detections"] = detections
        self._publish_snapshot()

    def update_latest_image(self, image: dict):
        self._observatory_state["latest_image"] = image
        self._publish_snapshot()

    def add_discovery(self, count: int = 1):
        self._observatory_state["discoveries"] += count
        self._publish_snapshot()

    def add_hypothesis(self, count: int = 1):
        self._observatory_state["hypotheses"] += count
        self._publish_snapshot()

    def add_alert(self, level: str, message: str):
        alert = {
            "id": f"a{len(self._alert_history) + 1}",
            "level": level,
            "time": datetime.now().strftime("%H:%M"),
            "message": message,
            "read": False,
        }
        self._alert_history.insert(0, alert)
        if len(self._alert_history) > self._max_alerts:
            self._alert_history = self._alert_history[:self._max_alerts]
        self._event_bus.publish("new_alert", alert)

    def _add_log(self, level: str, message: str):
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "message": message,
        }
        self._log_history.insert(0, entry)
        if len(self._log_history) > self._max_logs:
            self._log_history = self._log_history[:self._max_logs]

    def get_alerts(self, unread_only: bool = False) -> list:
        if unread_only:
            return [a for a in self._alert_history if not a["read"]]
        return list(self._alert_history)

    def get_logs(self, level: str = "", limit: int = 50) -> list:
        result = self._log_history
        if level:
            result = [e for e in result if e["level"].upper() == level.upper()]
        return result[:limit]

    def mark_alert_read(self, alert_id: str) -> bool:
        for a in self._alert_history:
            if a["id"] == alert_id:
                a["read"] = True
                return True
        return False

    def build_snapshot(self, ws_client_count: int = 0) -> ObservatorySnapshot:
        return ObservatorySnapshot(
            status=self._observatory_state["status"],
            uptime_hours=(time.time() - self._start_time) / 3600.0,
            discoveries=self._observatory_state["discoveries"],
            hypotheses=self._observatory_state["hypotheses"],
            ws_clients=ws_client_count,
            current_target=self._observatory_state["current_target"],
            queue=self._observatory_state["queue"],
            devices=self._observatory_state["devices"],
            research_loop=self._observatory_state["research_loop"],
            detections=self._observatory_state["detections"],
            latest_image=self._observatory_state["latest_image"],
        )

    def _publish_snapshot(self):
        now = time.time() * 1000
        if now - self._last_snapshot_time < self._throttle_ms:
            return
        self._last_snapshot_time = now
        snapshot = self.build_snapshot()
        self._event_bus.publish("status_update", snapshot.to_dict())


class ConnectionManager:
    """WebSocket 连接生命周期管理"""

    def __init__(self, heartbeat_interval: int = 30, heartbeat_timeout: int = 90):
        self._connections: dict[str, Any] = {}
        self._last_heartbeat: dict[str, float] = {}
        self._lock = Lock()
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_timeout = heartbeat_timeout

    def register(self, client_id: str, ws):
        with self._lock:
            self._connections[client_id] = ws
            self._last_heartbeat[client_id] = time.time()
        logger.info(f"WS client connected: {client_id} (total: {len(self._connections)})")

    def unregister(self, client_id: str):
        with self._lock:
            self._connections.pop(client_id, None)
            self._last_heartbeat.pop(client_id, None)
        logger.info(f"WS client disconnected: {client_id} (total: {len(self._connections)})")

    def heartbeat(self, client_id: str):
        with self._lock:
            self._last_heartbeat[client_id] = time.time()

    def get_stale_clients(self) -> list[str]:
        now = time.time()
        stale = []
        with self._lock:
            for cid, last_hb in list(self._last_heartbeat.items()):
                if now - last_hb > self._heartbeat_timeout:
                    stale.append(cid)
        return stale

    async def broadcast(self, message: dict):
        data = json.dumps(message, ensure_ascii=False, default=str)
        dead = []
        for cid, ws in list(self._connections.items()):
            try:
                await ws.send(data)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.unregister(cid)

    async def send_to(self, client_id: str, message: dict):
        ws = self._connections.get(client_id)
        if ws:
            try:
                data = json.dumps(message, ensure_ascii=False, default=str)
                await ws.send(data)
            except Exception:
                self.unregister(client_id)

    async def cleanup_stale(self):
        stale = self.get_stale_clients()
        for cid in stale:
            logger.warning(f"WS client heartbeat timeout: {cid}")
            self.unregister(cid)

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    @property
    def active_client_ids(self) -> list[str]:
        return list(self._connections.keys())


class MessageSerializer:
    """消息序列化器 - 支持 JSON 和二进制混合序列化"""

    @staticmethod
    def serialize_status_update(snapshot: dict) -> str:
        return json.dumps({
            "type": "status_update",
            "data": snapshot,
        }, ensure_ascii=False, default=str)

    @staticmethod
    def serialize_queue_update(queue: list) -> str:
        return json.dumps({
            "type": "queue_update",
            "data": queue,
        }, ensure_ascii=False, default=str)

    @staticmethod
    def serialize_alert(alert: dict) -> str:
        return json.dumps({
            "type": "new_alert",
            "data": alert,
        }, ensure_ascii=False, default=str)

    @staticmethod
    def serialize_event(event_type: str, data: Any) -> str:
        return json.dumps({
            "type": event_type,
            "data": data,
        }, ensure_ascii=False, default=str)

    @staticmethod
    def serialize_error(code: str, message: str) -> str:
        return json.dumps({
            "type": "error",
            "code": code,
            "message": message,
        }, ensure_ascii=False)


async def start_heartbeat_loop(conn_mgr: ConnectionManager):
    """启动心跳检测循环"""
    while True:
        await asyncio.sleep(conn_mgr._heartbeat_interval)
        await conn_mgr.cleanup_stale()


async def start_broadcast_loop(conn_mgr: ConnectionManager, bridge: AgentStateBridge):
    """启动定期广播循环"""
    while True:
        await asyncio.sleep(2)
        snapshot = bridge.build_snapshot(conn_mgr.connection_count)
        await conn_mgr.broadcast({
            "type": "status_update",
            "data": snapshot.to_dict(),
        })
