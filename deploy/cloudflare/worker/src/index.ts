/**
 * Tianwen-AGI Cloudflare Worker
 * 
 * 架构：
 * 前端 → CF Worker → 分发到各服务
 */

import { handleChat } from './routes/chat';
import { handleRailwayProxy } from './routes/railway-proxy';
import { handleSessions } from './routes/sessions';
import { handleRag } from './routes/rag';
import { handleHallucination } from './routes/hallucination';
import { handleLlmTest } from './routes/llm-test';
import { handlePing } from './routes/ping';

// CORS 头配置
const CORS_HEADERS: Record<string, string> = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key, X-LLM-Provider',
  'Access-Control-Max-Age': '86400',
};

// 需要代理到 Railway 的路径前缀
const RAILWAY_PROXY_PATHS = [
  '/api/skychart',
  '/api/telescope',
  '/api/observatory',
  '/api/research',
  '/api/hypothesis',
  '/api/literature',
  '/api/data/',
  '/api/devices/',
  '/api/alerts',
  '/api/stats/',
  '/api/docs',
  '/api/workflow-engine',
  '/api/workflows',
  '/api/observation',
];

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const pathname = url.pathname;

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    try {
      // 路由分发
      if (pathname === '/api/chat' && request.method === 'POST') {
        return handleChat(request, env);
      }
      if (pathname === '/api/llm/test' && request.method === 'POST') {
        return handleLlmTest(request, env);
      }
      if (pathname === '/api/ping' && request.method === 'GET') {
        return handlePing();
      }
      if (pathname.startsWith('/api/sessions')) {
        return handleSessions(request, env, pathname);
      }
      if (pathname.startsWith('/api/rag')) {
        return handleRag(request, env, pathname);
      }
      if (pathname.startsWith('/api/hallucination')) {
        return handleHallucination(request, env);
      }
      if (RAILWAY_PROXY_PATHS.some(p => pathname.startsWith(p))) {
        return handleRailwayProxy(request, env, pathname, url.search);
      }
      if (pathname === '/' || pathname.endsWith('.html')) {
        return Response.redirect('https://tianwen-agi.pages.dev', 301);
      }

      return jsonResponse({ error: 'Not Found', path: pathname }, 404);
    } catch (err) {
      console.error('Worker error:', err);
      return jsonResponse({ error: 'Internal Server Error', detail: String(err) }, 500);
    }
  },
};

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}

// 类型定义
interface Env {
  MINIMAX_API_KEY: string;
  MINIMAX_GROUP_ID: string;
  RENDER_BACKEND: string;
  DB: D1Database;
  VECTORIZE: VectorizeIndex;
  AI: Ai;
}
