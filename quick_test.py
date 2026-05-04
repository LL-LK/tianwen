import httpx
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test():
    urls = [
        ('Railway Backend', 'https://tianwen-agi-production.up.railway.app/api/health'),
        ('Cloudflare Frontend', 'https://tianwen-agi.pages.dev/'),
        ('Cloudflare API Proxy', 'https://tianwen-agi.pages.dev/api/health'),
    ]
    
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for name, url in urls:
            try:
                r = await client.get(url)
                status = 'OK' if r.status_code == 200 else 'FAIL'
                print(f'[{status}] {name}: {r.status_code}')
                if r.status_code == 200:
                    try:
                        data = r.json()
                        build = data.get('build_id', 'unknown')
                        print(f'   build_id: {build}')
                    except:
                        ct = r.headers.get('content-type', 'unknown')
                        print(f'   Content-Type: {ct}')
            except Exception as e:
                print(f'[ERR] {name}: {e}')

asyncio.run(test())
