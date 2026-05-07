/**
 * Tianwen-AGI API Gateway - Cloudflare Worker
 *
 * 混合架构：
 * 前端 → CF Worker → Railway (状态性/私密性API)
 *                → CF Cache (无状态/可缓存API)
 *
 * WebSocket: CF Worker → Durable Object → Railway WebSocket
 */

const RAILWAY_URL = env.RENDER_BACKEND || "https://tianwen-agi-backend.onrender.com";
const RAILWAY_WS = env.RENDER_BACKEND ? env.RENDER_BACKEND.replace("https://", "wss://") : "wss://tianwen-agi-backend.onrender.com";
const FRONTEND_ORIGIN = "https://tianwen-agi.pages.dev";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": FRONTEND_ORIGIN,
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key, X-LLM-Provider, Sec-WebSocket-Key, Sec-WebSocket-Version",
  "Access-Control-Max-Age": "86400",
  "Access-Control-Expose-Headers": "Content-Length, Content-Type",
};

const CACHEABLE_PATHS = [
  "/api/ping",
  "/api/stats/",
  "/api/literature/search",
  "/api/literature/citation-network",
  "/api/telescope/catalog",
  "/api/skychart/",
  "/api/docs",
  "/api/enhancements/capabilities",
  "/api/mcp/tools",
];

const AUTH_REQUIRED_PATHS = [
  "/api/chat",
  "/api/cognitive",
  "/api/hypothesis/",
  "/api/telescope/",
  "/api/observatory/",
  "/api/workflow-engine/",
  "/api/rag/",
];

function isCacheable(path, method) {
  if (method !== "GET") return false;
  return CACHEABLE_PATHS.some((p) => path.startsWith(p));
}

function requiresAuth(path) {
  return AUTH_REQUIRED_PATHS.some((p) => path.startsWith(p));
}

export class WSRelay {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.clientSocket = null;
    this.railwaySocket = null;
    this.messageBuffer = [];
    this.connected = false;
  }

  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/ws/") && request.headers.get("Upgrade") === "websocket") {
      return this.handleWebSocket(request);
    }
    return new Response("Not Found", { status: 404 });
  }

  async handleWebSocket(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    try {
      const railwayUrl = `${RAILWAY_WS}${path}`;
      const workerUrl = new URL(request.url);

      const options = {
        io: { capabilities: ["binary"] },
        headers: {
          "Upgrade": "websocket",
          "Connection": "Upgrade",
          "Sec-WebSocket-Version": "13",
          "Sec-WebSocket-Key": request.headers.get("Sec-WebSocket-Key") || "",
        },
      };

      try {
        this.railwaySocket = new WebSocket(railwayUrl, options);

        await new Promise((resolve, reject) => {
          this.railwaySocket.addEventListener("open", () => {
            this.connected = true;
            resolve();
          }, { once: true });
          this.railwaySocket.addEventListener("error", (e) => {
            reject(new Error("Railway WebSocket connection failed"));
          }, { once: true });
          setTimeout(() => reject(new Error("Railway WebSocket timeout")), 10000);
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: "Cannot connect to backend WebSocket", detail: e.message }), {
          status: 502,
          headers: { "Content-Type": "application/json" },
        });
      }

      const { 0: client, 1: server } = new WebSocketPair();
      this.clientSocket = server;
      server.accept();

      this.railwaySocket.addEventListener("message", (event) => {
        if (server.readyState === WebSocket.OPEN) {
          server.send(event.data);
        }
      });

      this.railwaySocket.addEventListener("close", () => {
        this.connected = false;
        try { server.close(1001, "Backend disconnected"); } catch (e) {}
      });

      this.railwaySocket.addEventListener("error", () => {
        this.connected = false;
        try { server.close(1011, "Backend error"); } catch (e) {}
      });

      server.addEventListener("message", (event) => {
        if (this.railwaySocket && this.railwaySocket.readyState === WebSocket.OPEN) {
          this.railwaySocket.send(event.data);
        }
      });

      server.addEventListener("close", () => {
        this.connected = false;
        if (this.railwaySocket) {
          try { this.railwaySocket.close(1000, "Client disconnected"); } catch (e) {}
        }
      });

      return new Response(null, { status: 101, webSocket: client });

    } catch (e) {
      return new Response(JSON.stringify({ error: "WebSocket relay error", detail: e.message }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    if (path.startsWith("/ws/") && request.headers.get("Upgrade") === "websocket") {
      const relayId = env.WS_RELAY.idFromName(path);
      const relay = env.WS_RELAY.get(relayId);
      return relay.fetch(request);
    }

    const cacheKey = `https://cf-cache/${path}`;
    const cache = caches.default;

    if (isCacheable(path, request.method)) {
      const cached = await cache.match(cacheKey);
      if (cached) {
        const newHeaders = new Headers(cached.headers);
        newHeaders.set("X-Cache", "HIT");
        for (const [k, v] of Object.entries(CORS_HEADERS)) {
          newHeaders.set(k, v);
        }
        return new Response(cached.body, { status: cached.status, headers: newHeaders });
      }
    }

    let railwayUrl = `${RAILWAY_URL}${path}`;
    if (url.search) railwayUrl += url.search;

    const headers = {};
    for (const [k, v] of request.headers.entries()) {
      if (!["host", "cf-", "x-forwarded-proto"].includes(k.toLowerCase())) {
        headers[k] = v;
      }
    }
    headers["X-Forwarded-Host"] = url.host;
    headers["X-Forwarded-Proto"] = "https";
    headers["Via"] = "cf-worker";

    let railwayResponse;
    try {
      railwayResponse = await fetch(railwayUrl, {
        method: request.method,
        headers,
        body: request.body ? await request.clone().arrayBuffer() : undefined,
        redirect: "manual",
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: "Railway unreachable", detail: e.message }), {
        status: 503,
        headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
      });
    }

    const responseHeaders = new Headers();
    for (const [k, v] of railwayResponse.headers.entries()) {
      if (!["transfer-encoding", "connection", "keep-alive"].includes(k.toLowerCase())) {
        responseHeaders.set(k, v);
      }
    }
    for (const [k, v] of Object.entries(CORS_HEADERS)) {
      responseHeaders.set(k, v);
    }
    responseHeaders.set("X-Backend", "railway");
    responseHeaders.set("X-Request-Id", crypto.randomUUID());

    if (isCacheable(path, request.method) && railwayResponse.status === 200) {
      const cacheResponse = new Response(railwayResponse.body, {
        status: railwayResponse.status,
        headers: responseHeaders,
      });
      const surrogateKey = path.replace(/\//g, "_").replace(/^_/, "") + "_" + railwayResponse.status;
      cacheResponse.headers.set("Cache-Control", "public, max-age=300, stale-while-revalidate=600");
      cacheResponse.headers.set("Surrogate-Key", surrogateKey);
      ctx.waitUntil(cache.put(cacheKey, cacheResponse.clone()));
      responseHeaders.set("X-Cache", "MISS");
    }

    return new Response(railwayResponse.body, {
      status: railwayResponse.status,
      statusText: railwayResponse.statusText,
      headers: responseHeaders,
    });
  },
};
