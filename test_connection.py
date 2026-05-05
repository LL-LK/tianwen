#!/usr/bin/env python3
"""
天问-AGI 前后端连接测试脚本
检查前后端连接情况、API 可用性、WebSocket 连接等
"""

import sys
import json
import time
import asyncio
import aiohttp
from typing import Dict, Any, Optional


class ConnectionTester:
    """连接测试器"""
    
    def __init__(self, backend_url: str = "https://tianwen-agi-production.up.railway.app"):
        self.backend_url = backend_url
        self.api_base = f"{backend_url}/api"
        self.ws_url = backend_url.replace('https://', 'wss://').replace('http://', 'ws://')
        self.results: Dict[str, Any] = {}
    
    async def test_http_api(self) -> Dict[str, Any]:
        """测试 HTTP API 连接"""
        print("\n" + "="*60)
        print("🔍 测试 HTTP API 连接")
        print("="*60)
        
        result = {
            "backend_url": self.backend_url,
            "api_base": self.api_base,
            "tests": {}
        }
        
        # 测试 1: /api/ping 端点
        print(f"\n1. 测试 /api/ping 端点...")
        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/ping", timeout=10) as resp:
                    latency = (time.time() - start_time) * 1000
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   ✅ 成功! 状态码: {resp.status}, 延迟: {latency:.0f}ms")
                        print(f"   响应: {json.dumps(data, ensure_ascii=False)}")
                        result["tests"]["ping"] = {"status": "success", "latency_ms": latency, "data": data}
                    else:
                        print(f"   ❌ 失败! 状态码: {resp.status}")
                        result["tests"]["ping"] = {"status": "error", "status_code": resp.status}
        except Exception as e:
            print(f"   ❌ 异常: {type(e).__name__}: {e}")
            result["tests"]["ping"] = {"status": "error", "error": str(e)}
        
        # 测试 2: /api/health 端点
        print(f"\n2. 测试 /api/health 端点...")
        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/health", timeout=10) as resp:
                    latency = (time.time() - start_time) * 1000
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   ✅ 成功! 状态码: {resp.status}, 延迟: {latency:.0f}ms")
                        print(f"   版本: {data.get('version', 'N/A')}")
                        print(f"   状态: {data.get('status', 'N/A')}")
                        result["tests"]["health"] = {"status": "success", "latency_ms": latency, "data": data}
                    else:
                        print(f"   ⚠️  状态码: {resp.status} (可能需要认证)")
                        result["tests"]["health"] = {"status": "warning", "status_code": resp.status}
        except Exception as e:
            print(f"   ❌ 异常: {type(e).__name__}: {e}")
            result["tests"]["health"] = {"status": "error", "error": str(e)}
        
        # 测试 3: CORS 检查
        print(f"\n3. 测试 CORS 配置...")
        try:
            headers = {
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
            async with aiohttp.ClientSession() as session:
                async with session.options(f"{self.api_base}/ping", headers=headers, timeout=10) as resp:
                    allow_origin = resp.headers.get("Access-Control-Allow-Origin", "")
                    allow_methods = resp.headers.get("Access-Control-Allow-Methods", "")
                    print(f"   ✅ OPTIONS 请求成功")
                    print(f"   Access-Control-Allow-Origin: {allow_origin}")
                    print(f"   Access-Control-Allow-Methods: {allow_methods}")
                    result["tests"]["cors"] = {
                        "status": "success",
                        "allow_origin": allow_origin,
                        "allow_methods": allow_methods
                    }
        except Exception as e:
            print(f"   ⚠️  CORS 测试异常: {e}")
            result["tests"]["cors"] = {"status": "warning", "error": str(e)}
        
        return result
    
    async def test_websocket(self) -> Dict[str, Any]:
        """测试 WebSocket 连接"""
        print("\n" + "="*60)
        print("🔌 测试 WebSocket 连接")
        print("="*60)
        
        result = {
            "ws_url": f"{self.ws_url}/ws/observatory",
            "tests": {}
        }
        
        print(f"\n尝试连接到 {result['ws_url']}...")
        try:
            start_time = time.time()
            session = aiohttp.ClientSession()
            ws = await session.ws_connect(result["ws_url"], timeout=10)
            latency = (time.time() - start_time) * 1000
            print(f"   ✅ WebSocket 连接成功! 延迟: {latency:.0f}ms")
            result["tests"]["connect"] = {"status": "success", "latency_ms": latency}
            
            # 测试发送消息
            print(f"\n发送测试消息...")
            await ws.send_str("get_status")
            
            # 等待响应（最多 5 秒）
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=5)
                if msg.type == aiohttp.WSMsgType.TEXT:
                    print(f"   ✅ 收到响应")
                    try:
                        data = json.loads(msg.data)
                        print(f"   消息类型: {data.get('type', 'N/A')}")
                    except:
                        print(f"   消息内容: {msg.data[:100]}")
                    result["tests"]["message"] = {"status": "success"}
            except asyncio.TimeoutError:
                print(f"   ⚠️  等待响应超时")
                result["tests"]["message"] = {"status": "timeout"}
            
            await ws.close()
            await session.close()
            print(f"   连接已关闭")
            
        except Exception as e:
            print(f"   ❌ WebSocket 连接失败: {type(e).__name__}: {e}")
            result["tests"]["connect"] = {"status": "error", "error": str(e)}
        
        return result
    
    def generate_summary(self, http_result: Dict[str, Any], ws_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试摘要"""
        print("\n" + "="*60)
        print("📊 测试总结")
        print("="*60)
        
        summary = {
            "backend_url": self.backend_url,
            "overall_status": "unknown",
            "http_api": {},
            "websocket": {},
            "recommendations": []
        }
        
        # HTTP API 状态
        http_tests = http_result.get("tests", {})
        ping_ok = http_tests.get("ping", {}).get("status") == "success"
        health_ok = http_tests.get("health", {}).get("status") in ["success", "warning"]
        
        if ping_ok:
            summary["http_api"]["status"] = "healthy"
            print("\n✅ HTTP API: 健康")
            if "ping" in http_tests and "latency_ms" in http_tests["ping"]:
                print(f"   延迟: {http_tests['ping']['latency_ms']:.0f}ms")
        elif health_ok:
            summary["http_api"]["status"] = "partially_healthy"
            print("\n⚠️ HTTP API: 部分可用")
        else:
            summary["http_api"]["status"] = "unhealthy"
            print("\n❌ HTTP API: 不可用")
        
        # WebSocket 状态
        ws_tests = ws_result.get("tests", {})
        ws_ok = ws_tests.get("connect", {}).get("status") == "success"
        
        if ws_ok:
            summary["websocket"]["status"] = "connected"
            print("✅ WebSocket: 已连接")
        else:
            summary["websocket"]["status"] = "disconnected"
            print("❌ WebSocket: 未连接")
        
        # 总体状态
        if ping_ok and ws_ok:
            summary["overall_status"] = "healthy"
            print("\n🎉 总体状态: 完全健康！前后端连接正常")
        elif ping_ok:
            summary["overall_status"] = "partially_healthy"
            print("\n⚠️  总体状态: 部分可用（HTTP API 正常，WebSocket 可能有问题）")
        else:
            summary["overall_status"] = "unhealthy"
            print("\n❌ 总体状态: 不可用")
        
        # 建议
        if not ping_ok:
            summary["recommendations"].append("检查后端服务是否正在运行")
            summary["recommendations"].append("确认后端 URL 配置正确")
            summary["recommendations"].append("检查网络连接和防火墙设置")
        
        if not ws_ok and ping_ok:
            summary["recommendations"].append("检查 WebSocket 端点配置")
            summary["recommendations"].append("确认后端支持 WebSocket 连接")
        
        # 前端配置说明
        print(f"\n📝 前端配置:")
        print(f"   当前后端地址: {self.backend_url}")
        print(f"   前端中通过 BACKEND_URL 变量配置")
        print(f"   如果需要本地开发，可以修改为 http://localhost:5000")
        
        return summary
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 天问-AGI 前后端连接测试")
        print(f"后端地址: {self.backend_url}")
        
        http_result = await self.test_http_api()
        ws_result = await self.test_websocket()
        summary = self.generate_summary(http_result, ws_result)
        
        self.results = {
            "http_api": http_result,
            "websocket": ws_result,
            "summary": summary,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 保存结果
        with open("/tmp/connection_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 测试结果已保存到: /tmp/connection_test_results.json")
        
        return self.results


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="天问-AGI 前后端连接测试")
    parser.add_argument("--backend", type=str, 
                       default="https://tianwen-agi-production.up.railway.app",
                       help="后端 URL (默认: https://tianwen-agi-production.up.railway.app)")
    parser.add_argument("--local", action="store_true",
                       help="测试本地后端 (http://localhost:5000)")
    
    args = parser.parse_args()
    
    backend_url = "http://localhost:5000" if args.local else args.backend
    
    tester = ConnectionTester(backend_url)
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(0)
