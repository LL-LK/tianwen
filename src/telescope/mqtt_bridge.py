"""
天问-AGI MQTT 望远镜网桥
基于 StarWhisper/NGSS/src/module/UdpConnect.py MQTTPublisher 架构
实现与物理望远镜的 MQTT 通信协议
"""
import logging
logger = logging.getLogger(__name__)

import asyncio
import base64
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from xml.etree.ElementTree import Element, SubElement, tostring

try:
    import paho.mqtt.client as mqtt
    from paho.mqtt.client import Client, MQTTv311, MQTTv31
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False
    mqtt = None

from loguru import logger

# ============ 话题配置 ============
# topic.yaml 结构（StarWhisper风格）:
# nina_action:
#   xinglong:
#     telescope1:
#       topic: "ngss/telescope/1/nina/action"
# ftp_transfer:
#   xinglong:
#     telescope1:
#       topic: "ngss/telescope/1/ftp/schedule"


@dataclass
class TopicConfig:
    """MQTT 话题配置"""
    section: str  # 'nina_action' | 'ftp_transfer'
    location: str  # 'xinglong' | 'ali' | 'subei' 等
    telescope: str  # 'telescope1' | 'telescope2' ...
    topic: str  # 完整话题字符串
    qos: int = 1


class TopicRegistry:
    """
    话题注册表（StarWhisper topic.yaml 解析器）
    管理所有望远镜的 MQTT 话题
    """

    # 默认站点配置
    DEFAULT_SITES = {
        "xinglong": {
            "lat": 40.0, "lon": 116.5, "elevation": 900,
            "timezone": "Asia/Shanghai"
        },
        "ali": {
            "lat": 32.5, "lon": 80.0, "elevation": 4200,
            "timezone": "Asia/Shanghai"
        },
        "subei": {
            "lat": 28.0, "lon": 105.0, "elevation": 1100,
            "timezone": "Asia/Shanghai"
        }
    }

    # 话题模板
    TOPIC_TEMPLATES = {
        "nina_action": "ngss/telescope/{telescope_id}/nina/action",
        "ftp_transfer": "ngss/telescope/{telescope_id}/ftp/schedule",
        "status": "ngss/telescope/{telescope_id}/status",
        "telemetry": "ngss/telescope/{telescope_id}/telemetry",
        "alert": "ngss/telescope/{telescope_id}/alert",
    }

    def __init__(self):
        self.configs: Dict[str, List[TopicConfig]] = {
            "nina_action": [],
            "ftp_transfer": [],
            "status": [],
            "telemetry": [],
            "alert": []
        }
        self._load_default_topics()

    def _load_default_topics(self):
        """加载默认话题配置（最多60台望远镜）"""
        for site in ["xinglong", "ali", "subei"]:
            for i in range(1, 21):  # 每站20台
                telescope_id = f"telescope{i}"
                for section in ["nina_action", "ftp_transfer", "status"]:
                    template = self.TOPIC_TEMPLATES[section]
                    topic = template.format(telescope_id=telescope_id)
                    cfg = TopicConfig(
                        section=section,
                        location=site,
                        telescope=telescope_id,
                        topic=f"{site}/{topic}"
                    )
                    self.configs[section].append(cfg)

    def get_topic(self, section: str, location: str, telescope: str) -> Optional[str]:
        """查询指定望远镜的话题"""
        for cfg in self.configs.get(section, []):
            if cfg.location == location and cfg.telescope == telescope:
                return cfg.topic
        return None

    def get_all_topics(self, section: str) -> List[str]:
        """获取所有话题"""
        return [cfg.topic for cfg in self.configs.get(section, [])]

    def register_topic(self, cfg: TopicConfig):
        """注册自定义话题"""
        if cfg.section not in self.configs:
            self.configs[cfg.section] = []
        self.configs[cfg.section].append(cfg)


# ============ MQTT 发布者 ============
# 基于 StarWhisper UdpConnect.py MQTTPublisher 类

class MQTTPublisher:
    """
    MQTT 发布者（移植自 StarWhisper UdpConnect.py）
    用于向望远镜发送调度指令和拍摄序列
    """

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        username: str = "",
        password: str = "",
        client_id: str = ""
    ):
        if not HAS_MQTT:
            raise RuntimeError("请安装 paho-mqtt: pip install paho-mqtt")

        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id or f"tianwen-mqtt-{int(time.time())}"

        self.client = Client(
            client_id=self.client_id,
            protocol=MQTTv311,
            clean_session=True
        )

        # 回调
        self._on_connect_cb: Optional[Callable] = None
        self._on_message_cb: Optional[Callable] = None
        self._on_publish_cb: Optional[Callable] = None

        # 话题注册
        self.topics = TopicRegistry()

        # 重发机制
        self.last_payload: Optional[str] = None
        self.last_topic: Optional[str] = None
        self.success_received = threading.Event()

        # 状态
        self._connected = False
        self._lock = threading.Lock()

        # 设置回调
        self.client.on_connect = self._on_connect
        self.client.on_publish = self._on_publish
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self._connected = True
            logger.info(f"[MQTT] Connected to {self.broker}:{self.port}")
            if self._on_connect_cb:
                self._on_connect_cb(rc)
        else:
            logger.warning(f"[MQTT] Connection failed, rc={rc}")
            self._connected = False

    def _on_publish(self, client, userdata, mid):
        """发布回调"""
        logger.debug(f"[MQTT] Published mid={mid}")
        if self._on_publish_cb:
            self._on_publish_cb(mid)

    def _on_message(self, client, userdata, msg):
        """消息接收回调"""
        try:
            payload = msg.payload.decode()
            logger.debug(f"[MQTT] Received '{payload}' on '{msg.topic}'")
            if payload == "Receive failed":
                self._republish()
            elif payload == "Receive success":
                self.success_received.set()
            if self._on_message_cb:
                self._on_message_cb(msg.topic, payload)
        except Exception as e:
            logger.error(f"[MQTT] Message parse error: {e}")

    def _republish(self):
        """重发上一条消息"""
        if self.last_payload and self.last_topic:
            logger.info(f"[MQTT] Republishing to {self.last_topic}")
            self.publish(self.last_topic, self.last_payload)

    def connect(self, timeout: int = 10) -> bool:
        """
        连接到 MQTT 代理
        返回: 是否连接成功
        """
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        try:
            logger.info(f"[MQTT] Connecting to {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()

            # 等待连接建立
            start = time.time()
            while not self._connected and (time.time() - start) < timeout:
                time.sleep(0.1)

            if self._connected:
                # 订阅状态话题
                status_topics = self.topics.get_all_topics("status")
                for t in status_topics:
                    self.client.subscribe(t, qos=1)
                logger.info(f"[MQTT] Connected, subscribed to {len(status_topics)} status topics")
                return True
            else:
                logger.error("[MQTT] Connection timeout")
                return False

        except Exception as e:
            logger.error(f"[MQTT] Connect error: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        self._connected = False
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("[MQTT] Disconnected")

    def publish(self, topic: str, payload: str, qos: int = 1, retain: bool = False) -> int:
        """
        发布消息
        返回: mid (消息ID)
        """
        if not self._connected:
            logger.warning("[MQTT] Not connected, cannot publish")
            return -1

        with self._lock:
            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            if result.is_published:
                logger.debug(f"[MQTT] Published to {topic}, mid={result.mid}")
            else:
                logger.warning(f"[MQTT] Publish not completed to {topic}")
            return result.mid

    def publish_nina_action(
        self,
        location: str,
        telescope: str,
        schedule_xml: str
    ) -> bool:
        """
        发布 N.I.N.A. 拍摄指令（FTP传输方式）

        参数:
        location: 站点名如 'xinglong'
        telescope: 望远镜编号如 'telescope1'
        schedule_xml: N.I.N.A. 拍摄序列 XML

        返回: 是否发布成功
        """
        topic = self.topics.get_topic("ftp_transfer", location, telescope)
        if not topic:
            logger.error(f"[MQTT] Topic not found for {location}/{telescope}")
            return False

        # 计算 schedule 的 SHA256 哈希
        schedule_hash = hashlib.sha256(schedule_xml.encode()).hexdigest()

        # Base64 编码 + 哈希包装
        payload_dict = {
            "schedule": base64.b64encode(schedule_xml.encode()).decode("utf-8"),
            "hash": schedule_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "sender": "tianwen-agi"
        }
        payload = json.dumps(payload_dict)

        self.last_payload = payload
        self.last_topic = topic
        self.success_received.clear()

        mid = self.publish(topic, payload, qos=2)
        logger.info(f"[MQTT] Published N.I.N.A. schedule to {topic}, mid={mid}")

        # 等待确认（超时30秒）
        confirmed = self.success_received.wait(timeout=30)
        if confirmed:
            logger.info(f"[MQTT] Schedule confirmed by telescope")
        else:
            logger.warning(f"[MQTT] No confirmation received for schedule")

        return confirmed

    def publish_nina_action_direct(
        self,
        location: str,
        telescope: str,
        action_dict: Dict[str, Any]
    ) -> int:
        """
        直接发布 N.I.N.A. 动作指令（JSON格式）

        参数:
        action_dict: 动作字典，如 {"command": "slew", "ra": 10.68, "dec": 41.27}
        """
        topic = self.topics.get_topic("nina_action", location, telescope)
        if not topic:
            logger.error(f"[MQTT] Topic not found for {location}/{telescope}")
            return -1

        payload = json.dumps(action_dict)
        self.last_payload = payload
        self.last_topic = topic

        mid = self.publish(topic, payload, qos=1)
        logger.info(f"[MQTT] Published N.I.N.A. action to {topic}, mid={mid}")
        return mid

    def set_callbacks(
        self,
        on_connect: Callable = None,
        on_message: Callable = None,
        on_publish: Callable = None
    ):
        """设置回调函数"""
        if on_connect:
            self._on_connect_cb = on_connect
        if on_message:
            self._on_message_cb = on_message
        if on_publish:
            self._on_publish_cb = on_publish


# ============ MQTT 订阅者（望远镜状态监控） ============

class MQTTSubscriber:
    """
    MQTT 订阅者 - 接收望远镜状态反馈
    """

    def __init__(self, broker: str, port: int = 1883, client_id: str = ""):
        if not HAS_MQTT:
            raise RuntimeError("paho-mqtt not installed")

        self.broker = broker
        self.port = port
        self.client_id = client_id or f"tianwen-sub-{int(time.time())}"
        self.client = Client(client_id=self.client_id, protocol=MQTTv311)
        self._connected = False
        self._handlers: Dict[str, Callable] = {}
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info(f"[MQTT Sub] Connected to {self.broker}:{self.port}")
        else:
            logger.warning(f"[MQTT Sub] Connection failed rc={rc}")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = msg.payload.decode()
            logger.debug(f"[MQTT Sub] {topic}: {payload[:200]}")
            if topic in self._handlers:
                self._handlers[topic](payload)
        except Exception as e:
            logger.error(f"[MQTT Sub] Error handling {topic}: {e}")

    def subscribe(self, topic: str, handler: Callable[[str], None], qos: int = 1):
        """订阅话题并注册处理器"""
        self._handlers[topic] = handler
        if self._connected:
            self.client.subscribe(topic, qos=qos)
            logger.info(f"[MQTT Sub] Subscribed to {topic}")

    def start(self, topics: List[str] = None):
        """启动订阅"""
        if topics:
            for t in topics:
                self.client.subscribe(t, qos=1)
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()
        logger.info(f"[MQTT Sub] Started")

    def stop(self):
        """停止订阅"""
        self._connected = False
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("[MQTT Sub] Stopped")


# ============ 望远镜模拟器网桥 ============

class TelescopeBridge:
    """
    望远镜网桥 - 在模拟模式和真实MQTT模式间切换
    StarWhisper X-OPSTEP 数据管线的简化实现
    """

    def __init__(self, mode: str = "simulation"):
        """
        参数:
        mode: 'simulation' | 'mqtt' | 'hybrid'
        """
        self.mode = mode
        self.publisher: Optional[MQTTPublisher] = None
        self.subscriber: Optional[MQTTSubscriber] = None
        self._telescope_state: Dict[str, Any] = {}

        # 模拟模式状态
        self._sim_state = {
            "ra": 0.0,
            "dec": 0.0,
            "altitude": 0.0,
            "azimuth": 0.0,
            "slew_status": "idle",
            "tracking": False,
            "exposure_count": 0
        }

    def connect(self, broker: str = "localhost", port: int = 1883,
                username: str = "", password: str = "") -> bool:
        """连接MQTT代理"""
        if self.mode == "simulation":
            logger.info("[Bridge] Simulation mode, no MQTT connection needed")
            return True

        try:
            self.publisher = MQTTPublisher(broker, port, username, password)
            connected = self.publisher.connect()
            if connected and self.mode == "mqtt":
                self._setup_subscriber(broker, port)
            return connected
        except Exception as e:
            logger.error(f"[Bridge] MQTT connection failed: {e}")
            logger.info("[Bridge] Falling back to simulation mode")
            self.mode = "simulation"
            return True

    def _setup_subscriber(self, broker: str, port: int):
        """设置状态订阅"""
        if not self.publisher:
            return
        self.subscriber = MQTTSubscriber(broker, port)
        status_topics = self.publisher.topics.get_all_topics("status")
        for t in status_topics[:5]:  # 限制订阅数量
            self.subscriber.subscribe(t, self._handle_status)
        self.subscriber.start()

    def _handle_status(self, payload: str):
        """处理望远镜状态消息"""
        try:
            state = json.loads(payload)
            telescope_id = state.get("telescope_id", "unknown")
            self._telescope_state[telescope_id] = state
            logger.debug(f"[Bridge] Telescope {telescope_id} state updated")
        except Exception:
            pass

    def send_schedule(
        self,
        location: str,
        telescope: str,
        schedule_xml: str
    ) -> bool:
        """
        发送拍摄序列到望远镜
        """
        if self.mode == "simulation":
            logger.info(f"[Bridge Sim] Would send schedule to {location}/{telescope}")
            logger.debug(f"[Bridge Sim] XML size: {len(schedule_xml)} bytes")
            self._sim_state["exposure_count"] += schedule_xml.count("<Exposure")
            return True

        if self.publisher:
            return self.publisher.publish_nina_action(location, telescope, schedule_xml)
        return False

    def send_slew_command(
        self,
        location: str,
        telescope: str,
        ra: float,
        dec: float
    ) -> int:
        """发送指向指令"""
        action = {
            "command": "slew",
            "ra": ra,
            "dec": dec,
            "timestamp": datetime.utcnow().isoformat()
        }

        if self.mode == "simulation":
            logger.info(f"[Bridge Sim] Slew to RA={ra:.4f} Dec={dec:.4f}")
            self._sim_state["ra"] = ra
            self._sim_state["dec"] = dec
            self._sim_state["slew_status"] = "slewing"
            return 0

        if self.publisher:
            return self.publisher.publish_nina_action_direct(location, telescope, action)
        return -1

    def get_state(self, telescope_id: str = "telescope1") -> Dict[str, Any]:
        """获取望远镜状态"""
        if self.mode == "simulation":
            return self._sim_state.copy()
        return self._telescope_state.get(telescope_id, {})

    def disconnect(self):
        """断开所有连接"""
        if self.publisher:
            self.publisher.disconnect()
        if self.subscriber:
            self.subscriber.stop()
        logger.info("[Bridge] Disconnected")


# ============ 快速测试 ============

if __name__ == "__main__":
    logger.info("=== MQTT Telescope Bridge 测试 ===")
    logger.info(f"paho-mqtt 可用: {HAS_MQTT}")

    # 话题注册测试
    registry = TopicRegistry()
    topic = registry.get_topic("nina_action", "xinglong", "telescope1")
    logger.info(f"话题查询 (xinglong/telescope1/nina): {topic}")

    topic = registry.get_topic("ftp_transfer", "ali", "telescope5")
    logger.info(f"话题查询 (ali/telescope5/ftp): {topic}")

    # 网桥模拟模式测试
    bridge = TelescopeBridge(mode="simulation")
    bridge.connect()

    # 模拟发送
    from observation_scheduler import NINAXMLGenerator, ObservationTarget, Location
    target = ObservationTarget(
        name="M31", ra=10.6847, dec=41.2687,
        magnitude=3.4, priority=1, min_altitude=30,
        exposure_time=120, filters=["L"]
    )
    loc = Location("xinglong", 40.0, 116.5, 900)
    nina_gen = NINAXMLGenerator()
    xml = nina_gen.create_capture_sequence_xml(target, loc, num_exposures=3)

    result = bridge.send_schedule("xinglong", "telescope1", xml)
    logger.info(f"Schedule发送: {'成功' if result else '失败'}")

    # 指向指令
    mid = bridge.send_slew_command("xinglong", "telescope1", 10.6847, 41.2687)
    logger.info(f"Slew指令 mid={mid}")

    state = bridge.get_state()
    logger.info(f"望远镜状态: {state}")

    bridge.disconnect()
