/**
 * Tianwen-AGI API Worker
 * 
 * 架构：
 * 前端 → API Worker → Python Container (后端)
 * 
 * 使用 @cloudflare/containers 包的 Container 类
 */

import { Container } from "@cloudflare/containers";

// 扩展 Container 类，指定后端端口
class TianwenBackend extends Container {
  defaultPort = 5000;
}

// CORS 头配置
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key, X-LLM-Provider',
  'Access-Control-Max-Age': '86400',
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 处理 CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    // 为每个会话创建独立的容器实例
    // 使用 session_id 或创建一个共享实例
    let container;
    try {
      // 尝试获取容器实例
      // 注意：这里使用 nameFromString 来创建一个稳定的容器 ID
      const containerId = env.TIANWEN_BACKEND.idFromName('shared-backend');
      container = env.TIANWEN_BACKEND.get(containerId);
    } catch (e) {
      // 如果容器获取失败，返回错误
      return new Response(JSON.stringify({
        error: '容器服务不可用',
        detail: e.message,
      }), {
        status: 503,
        headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      });
    }

    // 转发请求到容器
    try {
      const response = await container.fetch(request);

      // 添加 CORS 头到响应
      const newHeaders = new Headers(response.headers);
      for (const [key, value] of Object.entries(CORS_HEADERS)) {
        newHeaders.set(key, value);
      }

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: newHeaders,
      });
    } catch (e) {
      return new Response(JSON.stringify({
        error: '后端服务不可达',
        detail: e.message,
      }), {
        status: 502,
        headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      });
    }
  },
};
