import httpx
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test():
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        # 测试 Cloudflare API 代理
        print('=== Cloudflare Pages API Proxy Test ===')
        r = await client.get('https://tianwen-agi.pages.dev/api/health')
        print(f'Status: {r.status_code}')
        print(f'Content-Type: {r.headers.get("content-type", "unknown")}')
        print(f'Location: {r.headers.get("location", "none")}')
        if r.status_code == 200:
            print(f'Body (first 200 chars): {r.text[:200]}')
        print()
        
        # 直接测试 Railway 后端
        print('=== Railway Backend Direct Test ===')
        r = await client.get('https://tianwen-agi-production.up.railway.app/api/health')
        print(f'Status: {r.status_code}')
        print(f'Content-Type: {r.headers.get("content-type", "unknown")}')
        if r.status_code == 200:
            try:
                data = r.json()
                print(f'Response: {str(data)[:200]}')
            except:
                print(f'Body: {r.text[:200]}')

asyncio.run(test())
