export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const backend = 'https://tianwen-agi-production-fa3e.up.railway.app';

  const targetUrl = backend + url.pathname + url.search;

  const modifiedRequest = new Request(targetUrl, {
    method: request.method,
    headers: request.headers,
    body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.arrayBuffer() : undefined,
    redirect: 'follow',
  });

  const response = await fetch(modifiedRequest);

  const newResponse = new Response(response.body, response);
  newResponse.headers.set('Access-Control-Allow-Origin', '*');
  newResponse.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  newResponse.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-API-Key');
  newResponse.headers.set('Access-Control-Max-Age', '86400');

  return newResponse;
}
