/**
 * ping.ts - 健康检查
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
};

export function handlePing(): Response {
  return new Response(JSON.stringify({
    status: 'ok',
    service: 'tianwen-agi-worker',
    timestamp: new Date().toISOString(),
    version: '2.0.0-cf',
  }), {
    status: 200,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
