/**
 * Tianwen-AGI API Worker + WebSocket Relay
 *
 * 架构：
 * 前端 → API Worker → Python Container (后端)
 * 前端 → WS Worker → Durable Object → Python Container WebSocket
 */

import { Container } from "@cloudflare/containers";

class TianwenBackend extends Container {
  defaultPort = 5000;
}

export class WebSocketRelay {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.backend = null;
    this.clientSocket = null;
    this.connected = false;
    this.messageBuffer = [];
  }

  async fetch(request) {
    const url = new URL(request.url);

    if (url.pathname.startsWith('/ws/') && request.headers.get('Upgrade') === 'websocket') {
      return this.handleWebSocket(request);
    }

    return this.handleHttp(request);
  }

  async handleWebSocket(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    try {
      const containerId = this.env.TIANWEN_BACKEND.idFromName('shared-backend');
      this.backend = this.env.TIANWEN_BACKEND.get(containerId);

      const upgradeHeader = request.headers.get('Upgrade');
      if (upgradeHeader !== 'websocket') {
        return new Response('Expected WebSocket', { status: 426 });
      }

      const headerString = [
        `GET ${path} HTTP/1.1`,
        `Host: localhost:5000`,
        `Upgrade: websocket`,
        `Connection: Upgrade`,
        `Sec-WebSocket-Key: ${request.headers.get('Sec-WebSocket-Key') || 'dGhlIHNhbXBsZSBub25jZQ=='}`,
        `Sec-WebSocket-Version: 13`,
        ...Array.from(request.headers.entries()).map(([k, v]) => `${k}: ${v}`),
        '', ''
      ].join('\r\n');

      const encoder = new TextEncoder();
      const backendResponse = await this.backend.fetch(new Request(`http://localhost:5000${path}`, {
        method: 'GET',
        headers: {
          'Upgrade': 'websocket',
          'Connection': 'Upgrade',
          'Sec-WebSocket-Key': request.headers.get('Sec-WebSocket-Key') || 'dGhlIHNhbXBsZSBub25jZQ==',
          'Sec-WebSocket-Version': '13',
        },
      }));

      if (backendResponse.status !== 101) {
        return new Response('Backend WebSocket upgrade failed', { status: 502 });
      }

      const { 0: client, 1: server } = new WebSocketPair();

      this.clientSocket = server;
      this.connected = true;

      server.accept();

      server.addEventListener('message', async (event) => {
        if (this.backend && this.connected) {
          try {
            await this.backend.fetch(new Request(`http://localhost:5000${path}`, {
              method: 'GET',
              headers: {
                'Upgrade': 'websocket',
                'Connection': 'Upgrade',
                'Sec-WebSocket-Key': request.headers.get('Sec-WebSocket-Key') || 'dGhlIHNhbXBsZSBub25jZQ==',
                'Sec-WebSocket-Version': '13',
              },
            }));
          } catch (e) {}
        }
      });

      server.addEventListener('close', () => {
        this.connected = false;
        this.clientSocket = null;
      });

      server.addEventListener('error', () => {
        this.connected = false;
      });

      return new Response(null, { status: 101, webSocket: client });

    } catch (e) {
      return new Response(JSON.stringify({ error: 'WebSocket setup failed', detail: e.message }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  async handleHttp(request) {
    const CORS_HEADERS = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key, X-LLM-Provider',
      'Access-Control-Max-Age': '86400',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    try {
      const containerId = this.env.TIANWEN_BACKEND.idFromName('shared-backend');
      const container = this.env.TIANWEN_BACKEND.get(containerId);
      const response = await container.fetch(request);

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
      return new Response(JSON.stringify({ error: 'Container unavailable', detail: e.message }), {
        status: 503,
        headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      });
    }
  }
}

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key, X-LLM-Provider, Upgrade, Sec-WebSocket-Key, Sec-WebSocket-Version, Sec-WebSocket-Extensions',
  'Access-Control-Max-Age': '86400',
  'Access-Control-Expose-Headers': 'Upgrade, Connection',
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname.startsWith('/ws/') && request.headers.get('Upgrade') === 'websocket') {
      const relayId = env.WEBSOCKET_RELAY.idFromName(url.pathname);
      const relay = env.WEBSOCKET_RELAY.get(relayId);
      return relay.fetch(request);
    }

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    try {
      const containerId = env.TIANWEN_BACKEND.idFromName('shared-backend');
      const container = env.TIANWEN_BACKEND.get(containerId);
      const response = await container.fetch(request);

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
      return new Response(JSON.stringify({ error: 'Backend unavailable', detail: e.message }), {
        status: 503,
        headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      });
    }
  },
};
