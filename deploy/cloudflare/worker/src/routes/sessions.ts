/**
 * sessions.ts - D1 会话管理
 */

import type { Env } from '../types';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Max-Age': '86400',
};

export async function handleSessions(request: Request, env: Env, pathname: string): Promise<Response> {
  const db = env.DB;

  // /api/sessions - GET list
  if (pathname === '/api/sessions' && request.method === 'GET') {
    try {
      const result = await db.prepare(
        'SELECT id, created_at, updated_at, json_extract(messages, "$") as messages FROM sessions ORDER BY updated_at DESC LIMIT 50'
      ).all();
      return jsonResponse({ sessions: result.results }, 200, CORS_HEADERS);
    } catch (err) {
      return jsonResponse({ error: String(err) }, 500, CORS_HEADERS);
    }
  }

  // /api/sessions/<id> - GET single
  const match = pathname.match(/^\/api\/sessions\/([^/]+)$/);
  if (match && request.method === 'GET') {
    const sessionId = match[1];
    try {
      const result = await db.prepare(
        'SELECT * FROM sessions WHERE id = ?'
      ).bind(sessionId).first();
      if (!result) {
        return jsonResponse({ error: 'Session not found' }, 404, CORS_HEADERS);
      }
      return jsonResponse({ session: result }, 200, CORS_HEADERS);
    } catch (err) {
      return jsonResponse({ error: String(err) }, 500, CORS_HEADERS);
    }
  }

  // /api/sessions/<id> - DELETE
  if (match && request.method === 'DELETE') {
    const sessionId = match[1];
    try {
      await db.prepare('DELETE FROM sessions WHERE id = ?').bind(sessionId).run();
      return jsonResponse({ success: true }, 200, CORS_HEADERS);
    } catch (err) {
      return jsonResponse({ error: String(err) }, 500, CORS_HEADERS);
    }
  }

  return jsonResponse({ error: 'Not Found' }, 404, CORS_HEADERS);
}

function jsonResponse(data: unknown, status = 200, extraHeaders?: Record<string, string>): Response {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extraHeaders,
  };
  return new Response(JSON.stringify(data), { status, headers });
}
