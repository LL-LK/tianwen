// Cloudflare Worker 环境变量类型
export interface Env {
  MINIMAX_API_KEY: string;
  MINIMAX_GROUP_ID: string;
  RAILWAY_BACKEND: string;
  DB: D1Database;
  VECTORIZE: VectorizeIndex;
  AI: Ai;
}
