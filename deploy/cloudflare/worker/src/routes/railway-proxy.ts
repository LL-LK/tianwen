/**
 * render-proxy.ts - 代理 astronomy 模块到 Render
 */

import type { Env } from '../types';

const RENDER_HEADERS = [
  'accept',
  'content-type',
  'content-length',
  'authorization',
  'x-api-key',
  'x-llm-provider',
  'origin',
  'user-agent',
];

export async function handleRailwayProxy(
  request: Request,
  env: Env,
  pathname: string,
  search: string
): Promise<Response> {
  const CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key, X-LLM-Provider',
    'Access-Control-Max-Age': '86400',
  };

  const backend = env.RENDER_BACKEND || 'https://tianwen-agi-backend.onrender.com';
  const targetUrl = backend + pathname + search;

  // 构建转发的 headers
  const headers = new Headers();
  for (const [key, value] of request.headers.entries()) {
    if (RENDER_HEADERS.includes(key.toLowerCase())) {
      headers.set(key, value);
    }
  }

  let body: ArrayBuffer | undefined;
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    try {
      body = await request.arrayBuffer();
    } catch (e) {
      console.error('Failed to read body:', e);
    }
  }

  try {
    const resp = await fetch(targetUrl, {
      method: request.method,
      headers,
      body,
      redirect: 'follow',
    });

    const respHeaders = new Headers();
    for (const [key, value] of resp.headers.entries()) {
      respHeaders.set(key, value);
    }
    for (const [key, value] of Object.entries(CORS_HEADERS)) {
      respHeaders.set(key, value);
    }

    return new Response(resp.body, {
      status: resp.status,
      statusText: resp.statusText,
      headers: respHeaders,
    });
  } catch (err) {
    console.error('Render proxy error:', err);
    return jsonResponse({
      error: '后端服务不可达',
      detail: String(err),
      target: targetUrl,
    }, 502, CORS_HEADERS);
  }
}

function jsonResponse(data: unknown, status = 200, extraHeaders?: Record<string, string>): Response {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extraHeaders,
  };
  return new Response(JSON.stringify(data), { status, headers });
}
