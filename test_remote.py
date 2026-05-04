import httpx
import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test():
    base = 'https://tianwen-agi.pages.dev'
    async with httpx.AsyncClient(base_url=base, timeout=15) as client:
        tests = [
            ('GET', '/api/health', {}),
            ('GET', '/api/observatory/status', {}),
            ('GET', '/api/telescope/status', {}),
            ('GET', '/api/telescope/catalog', {}),
            ('GET', '/api/skychart/coordinates', {'target': 'M31'}),
            ('GET', '/api/alerts', {}),
            ('GET', '/api/logs', {}),
            ('GET', '/api/stats/summary', {}),
            ('GET', '/api/docs', {}),
            ('POST', '/api/chat', {'message': '你好', 'session_id': 'test'}),
            ('POST', '/api/hypothesis/generate', {'topic': '系外行星', 'context': '测试'}),
            ('GET', '/api/data/miner', {'target': 'M31'}),
            ('GET', '/api/skychart', {'target': 'M31'}),
            ('GET', '/api/observation/data', {}),
        ]
        
        for method, path, params in tests:
            try:
                if method == 'GET':
                    r = await client.get(path, params=params)
                else:
                    r = await client.post(path, json=params)
                
                ok = 'OK' if r.status_code == 200 else 'FAIL'
                print(f'[{ok}] {method} {path} -> {r.status_code}')
                if r.status_code != 200:
                    print(f'   Error: {r.text[:150]}')
            except Exception as e:
                print(f'[ERR] {method} {path} -> {e}')

asyncio.run(test())
