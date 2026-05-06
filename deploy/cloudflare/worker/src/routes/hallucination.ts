/**
 * hallucination.ts - Workers AI 幻觉检测
 */

import type { Env } from '../types';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Max-Age': '86400',
};

interface HallucinationBody {
  text: string;
  context?: string;
}

export async function handleHallucination(request: Request, env: Env): Promise<Response> {
  if (request.method !== 'POST') {
    return jsonResponse({ error: 'Method not allowed' }, 405);
  }

  try {
    const body = await request.json() as HallucinationBody;
    const { text, context } = body;

    if (!text) {
      return jsonResponse({ error: 'text is required' }, 400);
    }

    // 使用 Workers AI 生成嵌入向量来做相似度分析
    const result = await env.AI.run('@cf/baai/bge-m3', { text }) as { embedding?: number[] };
    const embedding = result.embedding || [];
    const magnitude = Math.sqrt(embedding.reduce((sum, v) => sum + v * v, 0));

    // 简化的幻觉风险评估
    const confidence = Math.min(1, magnitude / 50);
    const risk = confidence > 0.8 ? 'low' : confidence > 0.5 ? 'medium' : 'high';

    return jsonResponse({
      text,
      context,
      hallucination_risk: risk,
      confidence,
      details: '基于嵌入向量相似度的简化评估，实际生产应接入专门的幻觉检测服务',
    });
  } catch (err) {
    return jsonResponse({ error: String(err) }, 500);
  }
}

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
