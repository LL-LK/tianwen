/**
 * /api/chat 路由 - MiniMax API 直连
 */

import type { Env } from '../types';

interface ChatRequest {
  message: string;
  session_id?: string;
  provider?: string;
  config?: Record<string, string>;
  system_prompt?: string;
  context?: string;
}

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key, X-LLM-Provider',
  'Access-Control-Max-Age': '86400',
};

export async function handleChat(request: Request, env: Env): Promise<Response> {
  try {
    const body = await request.json() as ChatRequest;
    const { message, session_id, provider = 'minimax', config = {}, system_prompt = '' } = body;

    if (!message) {
      return jsonResponse({ error: '消息不能为空' }, 400);
    }

    const sid = session_id || crypto.randomUUID();
    const apiKey = config.api_key || env.MINIMAX_API_KEY;
    const groupId = config.group_id || env.MINIMAX_GROUP_ID;
    const model = config.model || 'MiniMax-Text-01';

    const messages: { role: string; content: string }[] = [];
    if (system_prompt) {
      messages.push({ role: 'system', content: system_prompt });
    }
    messages.push({ role: 'user', content: message });

    const startTime = Date.now();

    const minimaxResp = await fetch('https://api.minimax.chat/v1/text/chatcompletion_pro', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages,
        stream: false,
        group_id: groupId,
      }),
    });

    const latencyMs = Date.now() - startTime;

    if (!minimaxResp.ok) {
      const errorText = await minimaxResp.text();
      console.error('MiniMax API error:', errorText);
      return jsonResponse({
        session_id: sid,
        cognitive: { intent: 'chat', entities: [], skills: [], complexity: 'low' },
        plan: { task_id: crypto.randomUUID(), subtasks: [], estimated_time: '0s', risks: [] },
        output: `我收到了你的消息：'${message.substring(0, 50)}'。当前 MiniMax API 不可用 (${minimaxResp.status})，请稍后再试。`,
        metrics: { tokens_used: 0, latency_ms: latencyMs, provider: 'MiniMax' },
        status: 'minimax_error',
        note: `MiniMax API 返回错误: ${minimaxResp.status}`,
      });
    }

    const minimaxData = await minimaxResp.json() as {
      choices?: { message?: { content?: string } }[];
      usage?: { total_tokens?: number };
    };
    const output = minimaxData.choices?.[0]?.message?.content || '';
    const tokensUsed = minimaxData.usage?.total_tokens || 0;

    // 存储会话到 D1
    try {
      await env.DB.prepare(`
        INSERT INTO sessions (id, messages, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          messages = json_insert(messages, '$[last]', json(?)),
          updated_at = excluded.updated_at
      `).bind(
        sid,
        JSON.stringify([{ role: 'user', content: message }, { role: 'assistant', content: output }]),
        new Date().toISOString(),
        JSON.stringify({ role: 'user', content: message })
      ).run();
    } catch (e) {
      console.error('Failed to save session:', e);
    }

    return jsonResponse({
      session_id: sid,
      cognitive: { intent: 'chat', entities: [], skills: [], complexity: 'low' },
      plan: { task_id: crypto.randomUUID(), subtasks: [], estimated_time: '0s', risks: [] },
      output,
      metrics: { tokens_used: tokensUsed, latency_ms: latencyMs, provider: 'MiniMax' },
      status: 'success',
    });

  } catch (err) {
    console.error('Chat error:', err);
    return jsonResponse({ error: String(err) }, 500);
  }
}

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  });
}
