import httpx
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test():
    base = 'https://tianwen-agi-production.up.railway.app'
    async with httpx.AsyncClient(base_url=base, timeout=15) as client:
        # 检查部署版本
        r = await client.get('/api/health')
        data = r.json()
        print('Health check:')
        print(f'  build_id: {data.get("build_id", "unknown")}')
        print(f'  version: {data.get("version", "unknown")}')
        print()
        
        # 检查新 API 路由是否存在
        routes = [
            '/api/skychart?target=M31',
            '/api/observation/data',
            '/api/hypothesis/generate',
            '/api/data/miner?target=M31',
        ]
        
        print('New routes check:')
        for route in routes:
            r = await client.get(route)
            status = 'EXISTS' if r.status_code != 404 else 'MISSING'
            print(f'  {route} -> {status} ({r.status_code})')
            if r.status_code == 404:
                print(f'    Response: {r.text[:100]}')

asyncio.run(test())
