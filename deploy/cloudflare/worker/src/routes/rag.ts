/**
 * rag.ts - Vectorize 向量搜索 RAG
 */

import type { Env } from '../types';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Max-Age': '86400',
};

export async function handleRag(request: Request, env: Env, pathname: string): Promise<Response> {
  const url = new URL(request.url);
  const query = url.searchParams.get('q') || url.searchParams.get('query');

  if (pathname === '/api/rag/hybrid-search' && request.method === 'GET' && query) {
    try {
      // 使用 Workers AI 生成嵌入向量
      const embedResult = await env.AI.run('@cf/baai/bge-m3', { text: query }) as { embedding?: number[] };
      const embedding = embedResult.embedding || [];

      // 查询 Vectorize
      const results = await env.VECTORIZE.query(embedding, { topK: 5 });

      return jsonResponse({
        query,
        results: results.matches.map((m) => ({
          id: m.id,
          score: m.score,
          text: (m.metadata as Record<string, unknown>)?.text || '',
          source: (m.metadata as Record<string, unknown>)?.source || '',
        })),
      });
    } catch (err) {
      return jsonResponse({ error: String(err) }, 500);
    }
  }

  return jsonResponse({ error: 'Not Found' }, 404);
}

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
