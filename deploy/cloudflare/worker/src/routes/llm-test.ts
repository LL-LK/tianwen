/**
 * llm-test.ts - LLM 连接测试
 */

import type { Env } from '../types';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
  'Access-Control-Max-Age': '86400',
};

interface LlmTestBody {
  api_key?: string;
  group_id?: string;
  model?: string;
}

export async function handleLlmTest(request: Request, env: Env): Promise<Response> {
  try {
    const body = await request.json() as LlmTestBody;
    const apiKey = body.api_key || env.MINIMAX_API_KEY;
    const groupId = body.group_id || env.MINIMAX_GROUP_ID;
    const model = body.model || 'MiniMax-Text-01';

    if (!apiKey) {
      return jsonResponse({
        success: false,
        error: 'MINIMAX_API_KEY 未配置',
        hint: '通过 wrangler secret set MINIMAX_API_KEY 设置',
      }, 400);
    }

    const startTime = Date.now();
    const resp = await fetch('https://api.minimax.chat/v1/text/chatcompletion_pro', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user', content: 'Hi' }],
        stream: false,
        group_id: groupId,
      }),
    });
    const latency = Date.now() - startTime;

    if (resp.ok) {
      const data = await resp.json() as { model?: string };
      return jsonResponse({
        success: true,
        provider: 'MiniMax',
        model: data.model || model,
        latency_ms: latency,
        message: '连接成功',
      });
    } else {
      const error = await resp.text();
      return jsonResponse({
        success: false,
        error: `API 返回错误: ${resp.status}`,
        detail: error,
        latency_ms: latency,
      }, 502);
    }
  } catch (err) {
    return jsonResponse({ success: false, error: String(err) }, 500);
  }
}

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
