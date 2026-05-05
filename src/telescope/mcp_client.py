"""
望远镜MCP客户端 - 重导出模块

本模块从 telescope.seestar_client 导入所有公共API，保持向后兼容。
原始实现位于 src/telescope/seestar_client.py
"""

from telescope.seestar_client import (
    HardwareInterfaceType,
    HardwareInterfaceConfig,
    BaseHardwareInterface,
    INDIInterface,
    ASCOMInterface,
    create_hardware_interface,
    SafetyCallback,
    SafetyProtocolManager,
    TelescopeStatus,
    TelescopePosition,
    ObservationTarget,
    SafetyCheckResult,
    SeestarMCPClient,
    create_client,
)

__all__ = [
    "HardwareInterfaceType",
    "HardwareInterfaceConfig",
    "BaseHardwareInterface",
    "INDIInterface",
    "ASCOMInterface",
    "create_hardware_interface",
    "SafetyCallback",
    "SafetyProtocolManager",
    "TelescopeStatus",
    "TelescopePosition",
    "ObservationTarget",
    "SafetyCheckResult",
    "SeestarMCPClient",
    "create_client",
]
