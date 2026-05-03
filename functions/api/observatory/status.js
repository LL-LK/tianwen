export async function onRequest(context) {
  const backend = 'https://tianwen-agi-production-fa3e.up.railway.app';
  const url = new URL(context.request.url);
  const targetUrl = backend + url.pathname + url.search;

  const response = await fetch(targetUrl, {
    method: context.request.method,
    headers: context.request.headers,
    body: context.request.method !== 'GET' && context.request.method !== 'HEAD'
      ? await context.request.arrayBuffer() : undefined,
  });

  const newResponse = new Response(response.body, response);
  newResponse.headers.set('Access-Control-Allow-Origin', '*');
  newResponse.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  newResponse.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-API-Key');
  return newResponse;
}
