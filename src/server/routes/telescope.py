# telescope.py - Telescope control routes extracted from server.py
# Functions: telescope_status, telescope_discover, telescope_connect, telescope_disconnect,
#            telescope_goto, telescope_plate_solve, telescope_tracking, telescope_expose,
#            telescope_observation_window, telescope_catalog

import logging
import asyncio
import sys
from quart import jsonify, request

logger = logging.getLogger("hermes_agi")

# Global telescope state
_telescope_client = None
_telescope_connection_type = None
_telescope_discovered_devices = []
_SKYCHART_AVAILABLE = False

# Helper functions from parent module
def _get_telescope_client():
    global _telescope_client
    if _telescope_client is None:
        try:
            from telescope.seestar_client import SeestarMCPClient
            _telescope_client = SeestarMCPClient()
            _telescope_client.enable_simulation(True)
        except ImportError:
            _telescope_client = None
    return _telescope_client


async def _discover_lan_devices(subnet: str = "192.168.1") -> list:
    """局域网设备发现 - 扫描常见望远镜端口"""
    discovered = []
    common_ports = [8765, 7624, 11111, 4030, 80, 8080]
    common_hosts = [
        "seestar.local", "seestar", "telescope.local",
        "stellarmate.local", "asiair.local", "raspberrypi.local"
    ]

    for host in common_hosts:
        for port in common_ports:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=1.0
                )
                writer.close()
                discovered.append({"host": host, "port": port, "method": "mDNS"})
            except Exception:
                pass

    for i in range(1, 20):
        host = f"{subnet}.{i}"
        for port in [8765, 7624]:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=0.3
                )
                writer.close()
                discovered.append({"host": host, "port": port, "method": "IP扫描"})
            except Exception:
                pass

    return discovered


def _detect_serial_ports() -> list:
    """检测串口设备（USB/物理导线连接）"""
    serial_ports = []
    try:
        import serial.tools.list_ports
        for port in serial.tools.list_ports.comports():
            serial_ports.append({
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid,
                "vid": port.vid,
                "pid": port.pid,
                "serial_number": port.serial_number,
                "manufacturer": port.manufacturer,
            })
    except ImportError:
        if sys.platform == "win32":
            for i in range(1, 33):
                serial_ports.append({
                    "device": f"COM{i}",
                    "description": f"串口 COM{i}",
                    "hwid": "",
                })
        else:
            import glob
            for pattern in ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/tty.SLAB*", "/dev/cu.*"]:
                for path in glob.glob(pattern):
                    serial_ports.append({
                        "device": path,
                        "description": path,
                        "hwid": "",
                    })
    return serial_ports


# Note: parse_coordinates and BUILTIN_CATALOG are telescope module globals
parse_coordinates = None
BUILTIN_CATALOG = {}


def init_telescope_routes(telescope_client, connection_type, discovered_devices, 
                          skychart_available, parse_coords, builtin_catalog):
    """Initialize global references from parent module"""
    global _telescope_client, _telescope_connection_type, _telescope_discovered_devices
    global _SKYCHART_AVAILABLE, parse_coordinates, BUILTIN_CATALOG
    _telescope_client = telescope_client
    _telescope_connection_type = connection_type
    _telescope_discovered_devices = discovered_devices
    _SKYCHART_AVAILABLE = skychart_available
    parse_coordinates = parse_coords
    BUILTIN_CATALOG = builtin_catalog


from datetime import datetime


async def telescope_status():
    """获取望远镜状态"""
    client = _get_telescope_client()
    if client is None:
        return jsonify({"error": "望远镜模块不可用", "code": "MODULE_UNAVAILABLE"}), 503

    if not client.is_connected:
        return jsonify({
            "connected": False,
            "status": "disconnected",
            "connection_type": _telescope_connection_type,
            "discovered_devices": _telescope_discovered_devices,
        })

    try:
        status = await client.get_status()
        pos = client.current_position
        return jsonify({
            "connected": True,
            "status": client.current_status.value,
            "position": {
                "ra": pos.ra,
                "dec": pos.dec,
                "alt": pos.alt,
                "az": pos.az,
            },
            "connection_type": _telescope_connection_type,
            "simulation_mode": client._simulation_mode,
            "raw_status": status,
        })
    except Exception as e:
        return jsonify({"error": str(e), "code": "STATUS_ERROR"}), 500


async def telescope_discover():
    """发现局域网和串口望远镜设备"""
    global _telescope_discovered_devices

    method = request.args.get("method", "all")

    lan_devices = []
    serial_devices = []

    if method in ("all", "lan"):
        subnet = request.args.get("subnet", "192.168.1")
        lan_devices = await _discover_lan_devices(subnet)

    if method in ("all", "serial"):
        serial_devices = _detect_serial_ports()

    _telescope_discovered_devices = {
        "lan": lan_devices,
        "serial": serial_devices,
        "total": len(lan_devices) + len(serial_devices),
    }

    return jsonify(_telescope_discovered_devices)


async def telescope_connect():
    """连接望远镜"""
    global _telescope_connection_type

    data = await request.get_json() or {}
    connection_type = data.get("type", "simulation")
    host = data.get("host", "localhost")
    port = data.get("port", 8765)
    serial_port = data.get("serial_port", None)

    client = _get_telescope_client()
    if client is None:
        return jsonify({"error": "望远镜模块不可用", "code": "MODULE_UNAVAILABLE"}), 503

    try:
        if connection_type == "simulation":
            client.enable_simulation(True)
            client.host = host
            client.port = port
            await client.connect()
            _telescope_connection_type = "simulation"

        elif connection_type == "lan":
            client.enable_simulation(False)
            client.host = host
            client.port = port
            success = await client.connect()
            if not success:
                return jsonify({"error": f"无法连接到 {host}:{port}", "code": "CONNECTION_FAILED"}), 503
            _telescope_connection_type = "lan"

        elif connection_type == "serial":
            client.enable_simulation(False)
            client.host = "serial"
            client.port = 0
            client._serial_port = serial_port
            await client.connect()
            _telescope_connection_type = "serial"

        elif connection_type == "ascom":
            from telescope.seestar_client import HardwareInterfaceType
            client.set_hardware_interface(HardwareInterfaceType.ASCOM, driver_id=data.get("driver_id"))
            client.enable_simulation(False)
            await client.connect()
            _telescope_connection_type = "ascom"

        elif connection_type == "indi":
            from telescope.seestar_client import HardwareInterfaceType
            client.set_hardware_interface(
                HardwareInterfaceType.INDI,
                host=data.get("indi_host", "localhost"),
                port=data.get("indi_port", 7624)
            )
            client.enable_simulation(False)
            await client.connect()
            _telescope_connection_type = "indi"

        elif connection_type == "mqtt":
            client.enable_mqtt(
                broker=data.get("mqtt_broker", "localhost"),
                port=data.get("mqtt_port", 1883),
                username=data.get("mqtt_username", ""),
                password=data.get("mqtt_password", ""),
                location=data.get("mqtt_location", "xinglong"),
                telescope_id=data.get("mqtt_telescope_id", "telescope1")
            )
            client.enable_simulation(False)
            await client.connect()
            _telescope_connection_type = "mqtt"

        else:
            return jsonify({"error": f"不支持的连接类型: {connection_type}", "code": "INVALID_TYPE"}), 400

        return jsonify({
            "success": True,
            "connection_type": _telescope_connection_type,
            "host": host,
            "port": port,
            "simulation_mode": client._simulation_mode,
        })

    except Exception as e:
        logger.error(f"望远镜连接失败: {e}")
        return jsonify({"error": f"连接失败: {str(e)}", "code": "CONNECTION_ERROR"}), 500


async def telescope_disconnect():
    """断开望远镜连接"""
    global _telescope_connection_type

    client = _get_telescope_client()
    if client is None or not client.is_connected:
        return jsonify({"error": "望远镜未连接", "code": "NOT_CONNECTED"}), 503

    try:
        await client.safe_shutdown()
        client.disable_mqtt()
        _telescope_connection_type = None
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e), "code": "DISCONNECT_ERROR"}), 500


async def telescope_goto():
    """
    GOTO指向目标

    Body: {"target": "M31"} 或 {"target": "10.6847,41.2687"}
    """
    client = _get_telescope_client()
    if client is None or not client.is_connected:
        return jsonify({"error": "望远镜未连接", "code": "NOT_CONNECTED"}), 503

    data = await request.get_json()
    if not data or "target" not in data:
        return jsonify({"error": "缺少 target 参数", "code": "MISSING_TARGET"}), 400

    target_str = data["target"].strip()

    try:
        from telescope.seestar_client import ObservationTarget

        if "," in target_str:
            parts = target_str.split(",")
            ra = float(parts[0].strip())
            dec = float(parts[1].strip())
            target_name = data.get("name", f"RA{ra}_DEC{dec}")
        else:
            coords = parse_coordinates(target_str) if _SKYCHART_AVAILABLE else None
            if coords:
                ra, dec = coords
                target_name = target_str
            else:
                return jsonify({"error": f"无法解析目标: {target_str}", "code": "TARGET_NOT_FOUND"}), 404

        target = ObservationTarget(
            name=target_name,
            ra=ra,
            dec=dec,
            priority=data.get("priority", 0.8),
            exposure_time=data.get("exposure_time", 60),
            filter=data.get("filter", "L"),
        )

        success = await client.goto_target(target)
        if success:
            return jsonify({
                "success": True,
                "target": target_name,
                "ra": ra,
                "dec": dec,
                "status": client.current_status.value,
            })
        else:
            return jsonify({"error": "GOTO失败，安全检查未通过或设备错误", "code": "GOTO_FAILED"}), 500

    except Exception as e:
        logger.error(f"望远镜GOTO失败: {e}")
        return jsonify({"error": str(e), "code": "GOTO_ERROR"}), 500


async def telescope_plate_solve():
    """执行Plate Solving校准"""
    client = _get_telescope_client()
    if client is None or not client.is_connected:
        return jsonify({"error": "望远镜未连接", "code": "NOT_CONNECTED"}), 503

    try:
        return jsonify({
            "success": True,
            "message": "Plate Solving功能需要ASTAP/Astrometry.net支持",
            "solved": False,
            "ra": client.current_position.ra,
            "dec": client.current_position.dec,
        })
    except Exception as e:
        return jsonify({"error": str(e), "code": "PLATE_SOLVE_ERROR"}), 500


async def telescope_tracking():
    """
    望远镜跟踪控制

    Body: {"action": "start"} 或 {"action": "stop"}
    """
    client = _get_telescope_client()
    if client is None or not client.is_connected:
        return jsonify({"error": "望远镜未连接", "code": "NOT_CONNECTED"}), 503

    data = await request.get_json()
    if not data or "action" not in data:
        return jsonify({"error": "缺少 action 参数", "code": "MISSING_ACTION"}), 400

    action = data["action"]

    try:
        if action == "start":
            client.current_status = client.telescope_status_enum().TRACKING if hasattr(client, 'telescope_status_enum') else type(client.current_status).TRACKING
        elif action == "stop":
            await client.abort()
        else:
            return jsonify({"error": f"无效操作: {action}", "code": "INVALID_ACTION"}), 400

        return jsonify({"success": True, "action": action, "status": client.current_status.value})
    except Exception as e:
        return jsonify({"error": str(e), "code": "TRACKING_ERROR"}), 500


async def telescope_expose():
    """
    执行曝光成像

    Body: {"exposure": 30, "count": 3, "target": "M31"}
    """
    client = _get_telescope_client()
    if client is None or not client.is_connected:
        return jsonify({"error": "望远镜未连接", "code": "NOT_CONNECTED"}), 503

    data = await request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空", "code": "EMPTY_BODY"}), 400

    exposure = float(data.get("exposure", 30))
    count = int(data.get("count", 1))
    target_name = data.get("target", "unknown")
    filter_name = data.get("filter", "L")

    try:
        success = await client.start_imaging(
            exposure_time=exposure,
            filter_name=filter_name,
            count=count,
        )

        if success:
            return jsonify({
                "success": True,
                "target": target_name,
                "exposure_sec": exposure,
                "frame_count": count,
                "filter": filter_name,
                "file_path": f"images/{target_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.fits",
            })
        else:
            return jsonify({"error": "曝光失败", "code": "EXPOSE_FAILED"}), 500

    except Exception as e:
        logger.error(f"望远镜曝光失败: {e}")
        return jsonify({"error": str(e), "code": "EXPOSE_ERROR"}), 500


async def telescope_observation_window():
    """
    计算目标观测窗口
    
    Query Params: target=M31&latitude=40.0
    """
    target_name = request.args.get("target", "M31")
    latitude = float(request.args.get("latitude", 40.0))
    
    coords = parse_coordinates(target_name) if _SKYCHART_AVAILABLE else None
    if not coords:
        if _SKYCHART_AVAILABLE:
            catalog_info = BUILTIN_CATALOG.get(target_name.upper(), {})
            coords = (catalog_info.get("ra"), catalog_info.get("dec"))
    
    if not coords or coords[0] is None:
        return jsonify({"error": f"无法解析目标: {target_name}"}), 400
    
    return jsonify({
        "target": target_name,
        "latitude": latitude,
        "ra": coords[0],
        "dec": coords[1],
    })


async def telescope_catalog():
    """
    获取内置天体星表
    
    Query Params: type=galaxy (可选过滤类型)
    """
    if not _SKYCHART_AVAILABLE:
        return jsonify({"error": "星图模块不可用", "code": "NOT_AVAILABLE"}), 503
    
    obj_type = request.args.get("type", None)
    
    catalog = {}
    for name, info in BUILTIN_CATALOG.items():
        if obj_type is None or info.get("type") == obj_type:
            catalog[name] = info
    
    return jsonify({
        "count": len(catalog),
        "type_filter": obj_type,
        "catalog": catalog
    })


def register_telescope_routes(
    app,
    telescope_client=None,
    connection_type=None,
    discovered_devices=None,
    serial_ports=None,
    get_telescope_client_func=None,
    discover_lan_func=None,
    detect_serial_func=None,
):
    """注册望远镜相关路由到 Flask/Quart app"""
    global _telescope_client, _telescope_connection_type, _telescope_discovered_devices
    if telescope_client is not None:
        _telescope_client = telescope_client
    if connection_type is not None:
        _telescope_connection_type = connection_type
    if discovered_devices is not None:
        _telescope_discovered_devices = discovered_devices

    routes = [
        ("/api/telescope/status", telescope_status, ["GET"]),
        ("/api/telescope/discover", telescope_discover, ["GET"]),
        ("/api/telescope/connect", telescope_connect, ["POST"]),
        ("/api/telescope/disconnect", telescope_disconnect, ["POST"]),
        ("/api/telescope/goto", telescope_goto, ["POST"]),
        ("/api/telescope/plate_solve", telescope_plate_solve, ["POST"]),
        ("/api/telescope/tracking", telescope_tracking, ["POST"]),
        ("/api/telescope/expose", telescope_expose, ["POST"]),
        ("/api/telescope/observation_window", telescope_observation_window, ["GET"]),
        ("/api/telescope/catalog", telescope_catalog, ["GET"]),
    ]

    for path, handler, methods in routes:
        app.add_url_rule(path, handler.__name__, handler, methods=methods)