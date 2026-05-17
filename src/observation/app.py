"""
天问-AGI 观测数据流水线 v2 (observation_app2)
基于 StarWhisper/NGSS/src/app/app2.py ProcessPoolExecutor 架构
实现多阶段并行处理：数据采集 → 传输 → 预处理 → 存储
"""
import logging
logger = logging.getLogger(__name__)

import asyncio
import base64
import concurrent.futures
import hashlib
import io
import json
import os
import queue
import shutil
import signal
import socket
import struct
import sys
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing as mp

from loguru import logger

# ============ 数据包定义 ============

@dataclass
class TelescopePacket:
    """
    望远镜数据包（StarWhisper X-OPSTEP 风格）
    从望远镜到数据中心的完整数据单元
    """
    packet_id: str
    telescope_id: str
    location: str
    timestamp: str  # ISO格式
    data_type: str  # 'image' | 'telemetry' | 'alert' | 'heartbeat'
    raw_data: bytes  # 原始数据（图像/TML/JSON）
    size_bytes: int
    checksum: str  # SHA256
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_bytes(cls, data: bytes) -> "TelescopePacket":
        """从字节流解析数据包"""
        # 格式: [4B magic][4B version][4B type][8B timestamp][4B size][N payload][64B checksum]
        if len(data) < 88:
            raise ValueError(f"Packet too short: {len(data)} bytes")

        magic = struct.unpack("!I", data[:4])[0]
        version = struct.unpack("!I", data[4:8])[0]
        type_id = struct.unpack("!I", data[8:12])[0]
        ts = struct.unpack("!Q", data[12:20])[0]
        payload_size = struct.unpack("!I", data[20:24])[0]

        data_types = ["image", "telemetry", "alert", "heartbeat"]
        data_type = data_types[type_id] if type_id < len(data_types) else "unknown"

        payload = data[24:24+payload_size]
        received_checksum = data[24+payload_size:24+payload_size+64].decode()

        packet_id = hashlib.sha256(data[:24+payload_size]).hexdigest()[:16]

        metadata = {}
        if data_type == "telemetry":
            try:
                metadata = json.loads(payload.decode())
            except Exception:
                pass

        return cls(
            packet_id=packet_id,
            telescope_id=metadata.get("telescope_id", "unknown"),
            location=metadata.get("location", "unknown"),
            timestamp=metadata.get("timestamp", datetime.fromtimestamp(ts).isoformat()),
            data_type=data_type,
            raw_data=payload,
            size_bytes=len(data),
            checksum=received_checksum,
            metadata=metadata
        )

    def verify(self) -> bool:
        """验证校验和"""
        calc = hashlib.sha256(self.raw_data).hexdigest()
        return calc == self.checksum

    def to_bytes(self) -> bytes:
        """序列化为字节流"""
        type_ids = {"image": 0, "telemetry": 1, "alert": 2, "heartbeat": 3}
        type_id = type_ids.get(self.data_type, 0)
        ts = int(time.time())

        header = struct.pack("!IIIQI",
            0x54414E57,  # MAGIC "TANW"
            2,  # version
            type_id,
            ts,
            len(self.raw_data)
        )

        checksum = hashlib.sha256(self.raw_data).hexdigest()
        return header + self.raw_data + checksum.encode()


# ============ 处理阶段定义 ============

@dataclass
class ProcessingStage:
    """处理阶段"""
    name: str
    queue_in: queue.Queue
    queue_out: queue.Queue
    workers: int = 2
    timeout: float = 30.0


# ============ 数据采集器 (Stage 1) ============

class DataCollector:
    """
    数据采集器 - 从MQTT/FTP接收原始数据
    对应 StarWhisper Data_pipeline.py 的采集阶段
    """

    def __init__(self, source: str = "mqtt", mqtt_broker: str = "localhost", mqtt_port: int = 1883):
        self.source = source
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._packet_callback: Optional[Callable] = None
        self._packet_queue: queue.Queue = queue.Queue(maxsize=1000)

    def set_callback(self, callback: Callable[[TelescopePacket], None]):
        """设置数据包回调"""
        self._packet_callback = callback

    def start(self):
        """启动采集"""
        self.running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()
        logger.info(f"[Collector] Started ({self.source})")

    def stop(self):
        """停止采集"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[Collector] Stopped")

    def _collect_loop(self):
        """采集循环"""
        if self.source == "mqtt":
            self._mqtt_collect()
        elif self.source == "dir":
            self._dir_collect()
        else:
            self._simulate_collect()

    def _mqtt_collect(self):
        """MQTT采集"""
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            logger.warning("[Collector] paho-mqtt not available, using simulation")
            self._simulate_collect()
            return

        client = mqtt.Client()

        def on_message(c, userdata, msg):
            try:
                packet = TelescopePacket.from_bytes(msg.payload)
                self._packet_queue.put(packet, timeout=1)
                if self._packet_callback:
                    self._packet_callback(packet)
            except Exception as e:
                logger.error(f"[Collector] Parse error: {e}")

        client.on_message = on_message

        try:
            client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            client.subscribe("ngss/telescope/#", qos=1)
            client.loop_start()
            logger.info(f"[Collector] MQTT connected to {self.mqtt_broker}:{self.mqtt_port}")

            while self.running:
                time.sleep(1)

            client.loop_stop()
            client.disconnect()
        except Exception as e:
            logger.error(f"[Collector] MQTT error: {e}")
            self._simulate_collect()

    def _dir_collect(self):
        """目录轮询采集（FTP备选）"""
        logger.info("[Collector] Directory polling mode")
        while self.running:
            time.sleep(5)

    def _simulate_collect(self):
        """模拟采集（开发/测试用）"""
        logger.info("[Collector] Simulation mode")
        packet_count = 0
        while self.running:
            time.sleep(10)  # 每10秒一个模拟包
            packet_count += 1
            payload = json.dumps({
                "telescope_id": f"telescope{packet_count % 3 + 1}",
                "location": "xinglong",
                "timestamp": datetime.utcnow().isoformat(),
                "type": "heartbeat",
                "status": "ok"
            }).encode()

            packet = TelescopePacket(
                packet_id=f"sim-{packet_count:06d}",
                telescope_id=f"telescope{packet_count % 3 + 1}",
                location="xinglong",
                timestamp=datetime.utcnow().isoformat(),
                data_type="heartbeat",
                raw_data=payload,
                size_bytes=len(payload),
                checksum=hashlib.sha256(payload).hexdigest(),
                metadata=json.loads(payload)
            )

            try:
                self._packet_queue.put(packet, timeout=1)
                if self._packet_callback:
                    self._packet_callback(packet)
            except queue.Full:
                pass

    def get_queue(self) -> queue.Queue:
        return self._packet_queue


# ============ 预处理器 (Stage 2) ============

class DataPreprocessor:
    """
    数据预处理器 - 并行处理FITS图像/遥测数据
    使用 ProcessPoolExecutor 实现CPU密集型并行
    """

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or max(1, mp.cpu_count() - 1)
        self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        self._input_queue: queue.Queue = queue.Queue(maxsize=500)
        self._output_queue: queue.Queue = queue.Queue(maxsize=500)
        self.running = False
        self._submit_thread: Optional[threading.Thread] = None
        self._futures: Dict[Any, str] = {}  # future -> packet_id

    def start(self):
        """启动预处理器"""
        self.running = True
        self._submit_thread = threading.Thread(target=self._submit_loop, daemon=True)
        self._submit_thread.start()
        logger.info(f"[Preprocessor] Started with {self.max_workers} workers")

    def stop(self):
        """停止预处理器"""
        self.running = False
        if self._submit_thread:
            self._submit_thread.join(timeout=5)
        self.executor.shutdown(wait=True, cancel_futures=True)
        logger.info("[Preprocessor] Stopped")

    def _submit_loop(self):
        """任务提交循环"""
        while self.running:
            try:
                packet = self._input_queue.get(timeout=1)
                future = self.executor.submit(self._process_packet, packet)
                self._futures[future] = packet.packet_id

                # 检查完成的future
                done = []
                for f in list(self._futures.keys()):
                    if f.done():
                        done.append(f)
                for f in done:
                    pid = self._futures.pop(f)
                    try:
                        result = f.result(timeout=1)
                        if result:
                            self._output_queue.put(result, timeout=1)
                    except Exception as e:
                        logger.error(f"[Preprocessor] {pid} failed: {e}")

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[Preprocessor] submit error: {e}")

    @staticmethod
    def _process_packet(packet: TelescopePacket) -> Optional[Dict]:
        """
        处理数据包（静态方法，运行在独立进程）
        """
        try:
            if packet.data_type == "image":
                return DataPreprocessor._process_image(packet)
            elif packet.data_type == "telemetry":
                return DataPreprocessor._process_telemetry(packet)
            else:
                return None
        except Exception as e:
            logger.error(f"ProcessPacket error: {e}")
            return None

    @staticmethod
    def _process_image(packet: TelescopePacket) -> Dict:
        """处理图像数据包"""
        # 检查FITS格式
        if packet.raw_data[:6] == b'Simple ':
            data_type = "fits"
        elif packet.raw_data[:2] == b'\xff\xd8':
            data_type = "jpeg"
        elif packet.raw_data[:4] == b'RIFF':
            data_type = "ser"
        else:
            data_type = "raw"

        # 简化处理：只提取元数据
        result = {
            "packet_id": packet.packet_id,
            "telescope_id": packet.telescope_id,
            "location": packet.location,
            "timestamp": packet.timestamp,
            "data_type": data_type,
            "size_bytes": len(packet.raw_data),
            "verified": packet.verify(),
            "metadata": packet.metadata
        }
        return result

    @staticmethod
    def _process_telemetry(packet: TelescopePacket) -> Dict:
        """处理遥测数据包"""
        try:
            tm = json.loads(packet.raw_data.decode())
        except Exception:
            tm = {}

        return {
            "packet_id": packet.packet_id,
            "telescope_id": packet.telescope_id,
            "location": packet.location,
            "timestamp": packet.timestamp,
            "data_type": "telemetry",
            "telemetry": tm,
            "verified": packet.verify()
        }

    def submit(self, packet: TelescopePacket):
        """提交数据包"""
        self._input_queue.put(packet, timeout=1)

    def get_output(self) -> Optional[Dict]:
        """获取处理结果（非阻塞）"""
        try:
            return self._output_queue.get_nowait()
        except queue.Empty:
            return None


# ============ 存储管理器 (Stage 3) ============

class StorageManager:
    """
    存储管理器 - 多级存储策略
    热存储: SSD/NVMe (最近1天)
    温存储: HDD (最近30天)
    冷存储: 归档 (超过30天)
    """

    def __init__(
        self,
        hot_path: str = "./data/hot",
        warm_path: str = "./data/warm",
        cold_path: str = "./data/cold",
        retention_days: Tuple[int, int] = (1, 30)
    ):
        self.hot_path = Path(hot_path)
        self.warm_path = Path(warm_path)
        self.cold_path = Path(cold_path)
        self.retention_days = retention_days  # (hot_days, warm_days)

        # 创建目录
        for p in [self.hot_path, self.warm_path, self.cold_path]:
            p.mkdir(parents=True, exist_ok=True)

        self.running = False
        self._input_queue: queue.Queue = queue.Queue(maxsize=200)
        self._worker: Optional[threading.Thread] = None
        self._stats = {
            "hot_stored": 0, "warm_stored": 0, "cold_stored": 0,
            "total_bytes": 0, "errors": 0
        }

    def start(self):
        """启动存储管理器"""
        self.running = True
        self._worker = threading.Thread(target=self._store_loop, daemon=True)
        self._worker.start()
        logger.info(f"[Storage] Started: hot={self.hot_path}, warm={self.warm_path}")

    def stop(self):
        """停止存储管理器"""
        self.running = False
        if self._worker:
            self._worker.join(timeout=10)
        logger.info(f"[Storage] Stopped. Stats: {self._stats}")

    def _store_loop(self):
        """存储循环"""
        while self.running:
            try:
                item = self._input_queue.get(timeout=1)
                processed_data, metadata = item

                # 决定存储层级
                ts = datetime.fromisoformat(metadata.get("timestamp", datetime.utcnow().isoformat()))
                age_days = (datetime.utcnow() - ts).total_seconds() / 86400

                if age_days < self.retention_days[0]:
                    storage_path = self.hot_path
                    self._stats["hot_stored"] += 1
                elif age_days < self.retention_days[1]:
                    storage_path = self.warm_path
                    self._stats["warm_stored"] += 1
                else:
                    storage_path = self.cold_path
                    self._stats["cold_stored"] += 1

                # 按日期/望远镜组织
                date_str = ts.strftime("%Y%m%d")
                telescope = metadata.get("telescope_id", "unknown")
                subdir = storage_path / date_str / telescope
                subdir.mkdir(parents=True, exist_ok=True)

                # 保存数据
                filename = f"{metadata['packet_id']}.{metadata.get('ext', 'dat')}"
                filepath = subdir / filename

                if isinstance(processed_data, bytes):
                    filepath.write_bytes(processed_data)
                elif isinstance(processed_data, dict):
                    with open(filepath, "w") as f:
                        json.dump(processed_data, f)
                else:
                    filepath.write_bytes(str(processed_data).encode())

                self._stats["total_bytes"] += len(processed_data) if isinstance(processed_data, bytes) else 0

            except queue.Empty:
                continue
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"[Storage] Error: {e}")

    def submit(self, processed_data: Any, metadata: Dict):
        """提交存储任务"""
        self._input_queue.put((processed_data, metadata), timeout=1)

    def get_stats(self) -> Dict:
        return self._stats.copy()


# ============ 主流水线 Orchestrator ============

class ObservationPipeline:
    """
    观测数据流水线 Orchestrator
    管理所有阶段的生命周期和拓扑关系
    移植自 StarWhisper app2.py ProcessPoolExecutor 架构
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.running = False

        # 阶段实例
        self.collector: Optional[DataCollector] = None
        self.preprocessor: Optional[DataPreprocessor] = None
        self.storage: Optional[StorageManager] = None

        # 连接器线程
        self._connector: Optional[threading.Thread] = None

        # 统计
        self._stats = {
            "start_time": None,
            "packets_received": 0,
            "packets_processed": 0,
            "packets_stored": 0
        }
        self._stats_lock = threading.Lock()

    def initialize(self, config: Dict[str, Any] = None):
        """初始化所有组件"""
        cfg = config or self.config

        # Stage 1: 采集器
        self.collector = DataCollector(
            source=cfg.get("source", "simulation"),
            mqtt_broker=cfg.get("mqtt_broker", "localhost"),
            mqtt_port=cfg.get("mqtt_port", 1883)
        )

        # Stage 2: 预处理器
        self.preprocessor = DataPreprocessor(
            max_workers=cfg.get("preprocess_workers", mp.cpu_count() - 1)
        )

        # Stage 3: 存储
        self.storage = StorageManager(
            hot_path=cfg.get("hot_path", "./data/hot"),
            warm_path=cfg.get("warm_path", "./data/warm"),
            cold_path=cfg.get("cold_path", "./data/cold")
        )

        # 设置采集器回调：直接将包送入预处理器
        self.collector.set_callback(self._on_packet_received)

        logger.info("[Pipeline] Initialized")

    def _on_packet_received(self, packet: TelescopePacket):
        """采集器收到包时的回调"""
        with self._stats_lock:
            self._stats["packets_received"] += 1

        if self.preprocessor:
            try:
                self.preprocessor.submit(packet)
            except queue.Full:
                logger.warning("[Pipeline] Preprocessor queue full, dropping packet")

    def start(self):
        """启动流水线"""
        if self.running:
            logger.warning("[Pipeline] Already running")
            return

        self.running = True
        self._stats["start_time"] = datetime.utcnow().isoformat()

        # 启动各阶段
        if self.collector:
            self.collector.start()
        if self.preprocessor:
            self.preprocessor.start()
        if self.storage:
            self.storage.start()

        # 启动连接器（把预处理器输出送到存储器）
        self._connector = threading.Thread(target=self._connect_stages, daemon=True)
        self._connector.start()

        logger.info("[Pipeline] Started")

    def stop(self):
        """停止流水线"""
        self.running = False

        if self.collector:
            self.collector.stop()
        if self.preprocessor:
            self.preprocessor.stop()
        if self.storage:
            self.storage.stop()

        if self._connector:
            self._connector.join(timeout=10)

        logger.info(f"[Pipeline] Stopped. Stats: {self._stats}")

    def _connect_stages(self):
        """连接预处理器和存储器"""
        while self.running:
            try:
                if self.preprocessor and self.storage:
                    result = self.preprocessor.get_output()
                    if result:
                        metadata = {
                            "packet_id": result.get("packet_id", ""),
                            "telescope_id": result.get("telescope_id", ""),
                            "location": result.get("location", ""),
                            "timestamp": result.get("timestamp", datetime.utcnow().isoformat()),
                            "data_type": result.get("data_type", "unknown"),
                            "ext": "json"
                        }
                        self.storage.submit(result, metadata)

                        with self._stats_lock:
                            self._stats["packets_processed"] += 1
                            self._stats["packets_stored"] += 1
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"[Pipeline] Connector error: {e}")

    def get_stats(self) -> Dict:
        """获取流水线统计"""
        stats = self._stats.copy()
        if self.storage:
            stats["storage"] = self.storage.get_stats()
        if self.preprocessor:
            stats["preprocessor_workers"] = self.preprocessor.max_workers
        return stats

    def run_blocking(self, duration_seconds: int = 60):
        """阻塞运行一段时间（用于测试）"""
        self.start()
        logger.info(f"[Pipeline] Running for {duration_seconds}s...")
        time.sleep(duration_seconds)
        self.stop()
        logger.info(f"[Pipeline] Final stats: {self.get_stats()}")


# ============ 快速测试 ============

if __name__ == "__main__":
    logger.info("=== Observation Pipeline 测试 ===")

    # 测试数据包序列化
    payload = json.dumps({"telescope_id": "telescope1", "status": "ok"}).encode()
    packet = TelescopePacket(
        packet_id="test-001",
        telescope_id="telescope1",
        location="xinglong",
        timestamp=datetime.utcnow().isoformat(),
        data_type="telemetry",
        raw_data=payload,
        size_bytes=len(payload),
        checksum=hashlib.sha256(payload).hexdigest()
    )

    logger.info(f"Packet ID: {packet.packet_id}")
    logger.info(f"Verify: {packet.verify()}")

    # 序列化/反序列化
    data = packet.to_bytes()
    logger.info(f"Serialized: {len(data)} bytes")

    # 测试流水线
    pipeline = ObservationPipeline()
    pipeline.initialize({
        "source": "simulation",
        "preprocess_workers": 2,
        "hot_path": "/tmp/tianwen_hot",
        "warm_path": "/tmp/tianwen_warm",
        "cold_path": "/tmp/tianwen_cold"
    })

    logger.info("\n启动流水线 (10秒)...")
    pipeline.run_blocking(duration_seconds=10)

    logger.info("\n流水线统计:")
    for k, v in pipeline.get_stats().items():
        logger.info(f"  {k}: {v}")
