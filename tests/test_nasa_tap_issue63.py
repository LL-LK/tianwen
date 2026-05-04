"""
NASA TAP查询测试脚本
验证Issue #63: KeplerExoplanetClient的NASA TAP查询实现

使用方法:
    python test_nasa_tap_issue63.py
"""

import asyncio
import sys
from pathlib import Path

import pytest

pytest.skip("NASA TAP tests require network access", allow_module_level=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.miner import DataMiner
from src.data.kepler import KeplerExoplanetClient


async def test_kepler_client_direct():
    """直接测试KeplerExoplanetClient"""
    print("=" * 60)
    print("测试1: 直接测试KeplerExoplanetClient")
    print("=" * 60)

    client = KeplerExoplanetClient()

    # 测试search_planets
    print("\n[1.1] 测试 search_planets(max_mass=10.0)...")
    planets = await client.search_planets(max_mass=10.0)
    print(f"    结果: 找到 {len(planets)} 颗行星")

    if planets:
        print(f"    第一颗: {planets[0].get('pl_name', 'unknown')}")
        has_disc_year = 'disc_year' in planets[0] and planets[0]['disc_year'] is not None
        print(f"    数据源: {'NASA TAP' if has_disc_year else 'mock fallback'}")
    else:
        print("    警告: 返回空列表!")

    # 测试get_lightcurve
    print("\n[1.2] 测试 get_lightcurve('Kepler-90 h', 'Kepler')...")
    try:
        times, fluxes = await client.get_lightcurve('Kepler-90 h', 'Kepler')
        print(f"    结果: {len(times)} 个时间点, {len(fluxes)} 个通量点")
    except Exception as e:
        print(f"    错误: {e}")

    # 测试get_stellar_params
    print("\n[1.3] 测试 get_stellar_params('Kepler-90')...")
    try:
        params = await client.get_stellar_params('Kepler-90')
        print(f"    结果: {params}")
    except Exception as e:
        print(f"    错误: {e}")

    return len(planets) > 0


async def test_data_miner_integration():
    """测试DataMiner对KeplerExoplanetClient的集成"""
    print("\n" + "=" * 60)
    print("测试2: DataMiner对KeplerExoplanetClient的集成")
    print("=" * 60)

    miner = DataMiner()

    # 测试fetch_exoplanet_data
    print("\n[2.1] 测试 DataMiner.fetch_exoplanet_data(max_mass=10.0)...")
    planets = await miner.fetch_exoplanet_data(max_mass=10.0)
    print(f"    结果: 找到 {len(planets)} 颗行星")

    if planets:
        print(f"    第一颗: {planets[0].get('pl_name', 'unknown')}")
        print(f"    hostname: {planets[0].get('hostname', 'unknown')}")
        print(f"    轨道周期: {planets[0].get('pl_orbper', 'unknown')} 天")
    else:
        print("    警告: 返回空列表!")

    # 测试fetch_lightcurve
    print("\n[2.2] 测试 DataMiner.fetch_lightcurve('Kepler-90 h', 'Kepler')...")
    try:
        times, fluxes = await miner.fetch_lightcurve('Kepler-90 h', 'Kepler')
        print(f"    结果: {len(times)} 个时间点, {len(fluxes)} 个通量点")
    except Exception as e:
        print(f"    错误: {e}")

    # 测试analyze_exoplanet_system
    print("\n[2.3] 测试 DataMiner.analyze_exoplanet_system('Kepler-90')...")
    result = await miner.analyze_exoplanet_system('Kepler-90', max_mass=10.0)
    if 'error' in result:
        print(f"    错误: {result['error']}")
    else:
        print(f"    结果: 发现 {result.get('n_planets', 0)} 颗行星")
        print(f"    恒星参数: {result.get('stellar_params', {})}")

    return len(planets) > 0


async def main():
    """主测试流程"""
    print("\n" + "#" * 60)
    print("# NASA TAP查询验证 - Issue #63")
    print("#" * 60)

    # 测试1: 直接测试KeplerExoplanetClient
    client_ok = await test_kepler_client_direct()

    # 测试2: DataMiner集成
    miner_ok = await test_data_miner_integration()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"[{'PASS' if client_ok else 'FAIL'}] KeplerExoplanetClient.search_planets()")
    print(f"[{'PASS' if miner_ok else 'FAIL'}] DataMiner集成KeplerExoplanetClient")

    if client_ok and miner_ok:
        print("\n验收标准通过!")
        return True
    else:
        print("\n验收标准未完全通过，需要进一步调查")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)