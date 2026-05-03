const BACKEND = 'https://tianwen-agi-production-fa3e.up.railway.app';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
  'Access-Control-Max-Age': '86400',
};

const SAFE_HEADERS = [
  'accept', 'accept-language', 'content-type', 'content-length',
  'authorization', 'x-api-key', 'user-agent', 'referer',
];

function cleanHeaders(original) {
  const cleaned = new Headers();
  for (const [key, value] of original.entries()) {
    const lower = key.toLowerCase();
    if (SAFE_HEADERS.includes(lower)) {
      cleaned.set(key, value);
    }
  }
  return cleaned;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }

  const targetUrl = BACKEND + url.pathname + url.search;

  const headers = cleanHeaders(request.headers);

  let body = undefined;
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    try {
      body = await request.arrayBuffer();
    } catch (e) {
      body = undefined;
    }
  }

  try {
    const backendResp = await fetch(targetUrl, {
      method: request.method,
      headers: headers,
      body: body,
      redirect: 'follow',
    });

    const respHeaders = new Headers(backendResp.headers);
    for (const [key, value] of Object.entries(CORS_HEADERS)) {
      respHeaders.set(key, value);
    }

    return new Response(backendResp.body, {
      status: backendResp.status,
      statusText: backendResp.statusText,
      headers: respHeaders,
    });
  } catch (err) {
    return new Response(JSON.stringify({
      error: '后端服务不可达',
      detail: err.message,
      backend: BACKEND,
    }), {
      status: 502,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
    });
  }
}
