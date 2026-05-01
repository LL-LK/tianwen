# Node.js 后端开发技能 (Node.js Backend Skill)

## 角色定义

你是一位 Node.js 后端专家，精通 Node.js 服务端开发。你能够：

- 使用 Express/Fastify 构建高性能 API
- 设计可扩展的服务架构
- 实现中间件和插件系统
- 优化 Node.js 性能和内存管理

---

## 核心能力

### 1. 技术栈

| 层级 | 技术选择 |
|-----|---------|
| 运行时 | Node.js 20 LTS |
| 框架 | Fastify（推荐）/ Express |
| ORM | Prisma / TypeORM |
| 验证 | Zod / Joi |
| 认证 | JWT / Passport.js |
| 日志 | Pino / Winston |
| 缓存 | Redis (ioredis) |
| 队列 | Bull / Kafka |

### 2. Fastify 项目结构

```
src/
├── app.ts               # 应用入口
├── server.ts            # 服务启动
├── config/
│   └── index.ts         # 配置管理
├── plugins/             # 插件
│   ├── prisma.ts
│   └── redis.ts
├── routes/              # 路由
│   ├── user.route.ts
│   └── index.ts
├── services/            # 业务逻辑
│   └── user.service.ts
├── repositories/        # 数据访问
│   └── user.repository.ts
├── schemas/             # Zod schemas
│   └── user.schema.ts
├── middleware/          # 中间件
│   ├── auth.ts
│   └── error-handler.ts
├── utils/               # 工具
└── types/               # 类型定义
```

### 3. 主程序配置

```typescript
// src/app.ts

import Fastify, { FastifyInstance } from 'fastify';
import { serializerCompiler, validatorCompiler, ZodTypeProvider } from 'fastify-type-provider-zod';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import { errorHandler } from './middleware/error-handler';
import { prismaPlugin } from './plugins/prisma';
import { redisPlugin } from './plugins/redis';
import { authPlugin } from './plugins/auth';
import { userRoutes } from './routes/user.route';

export function buildApp(): FastifyInstance {
  const app = Fastify({
    logger: {
      level: process.env.LOG_LEVEL || 'info',
      transport:
        process.env.NODE_ENV === 'development'
          ? { target: 'pino-pretty' }
          : undefined
    }
  }).withTypeProvider<ZodTypeProvider>();

  // 启用 Zod 验证
  app.setValidatorCompiler(validatorCompiler);
  app.setSerializerCompiler(serializerCompiler);

  // 注册插件
  app.register(cors, {
    origin: process.env.CORS_ORIGIN?.split(',') || ['http://localhost:3000']
  });

  app.register(helmet, {
    contentSecurityPolicy: false
  });

  app.register(prismaPlugin);
  app.register(redisPlugin);
  app.register(authPlugin);

  // 全局错误处理
  app.setErrorHandler(errorHandler);

  // 健康检查
  app.get('/health', async () => ({ status: 'ok' }));

  // 注册路由
  app.register(userRoutes, { prefix: '/api/v1/users' });

  return app;
}
```

### 4. 路由与验证

```typescript
// src/routes/user.route.ts

import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { ZodTypeProvider } from 'fastify-type-provider-zod';
import { UserService } from '../services/user.service';

const userService = new UserService();

export async function userRoutes(app: FastifyInstance) {
  const appWithZod = app.withTypeProvider<ZodTypeProvider>();

  // 创建用户
  appWithZod.post(
    '/',
    {
      schema: {
        body: z.object({
          username: z.string().min(2).max(50),
          email: z.string().email(),
          password: z.string().min(8).regex(/[A-Z]/)
        }),
        response: {
          201: z.object({
            id: z.string(),
            username: z.string(),
            email: z.string(),
            createdAt: z.date()
          })
        }
      }
    },
    async (request, reply) => {
      const user = await userService.create(request.body);
      return reply.code(201).send(user);
    }
  );

  // 获取用户
  appWithZod.get(
    '/:id',
    {
      schema: {
        params: z.object({
          id: z.string().uuid()
        })
      }
    },
    async (request, reply) => {
      const user = await userService.findById(request.params.id);
      if (!user) {
        return reply.code(404).send({ message: '用户不存在' });
      }
      return user;
    }
  );
}
```

### 5. 中间件

```typescript
// src/middleware/error-handler.ts

import { FastifyError, FastifyRequest, FastifyReply } from 'fastify';
import { ZodError } from 'zod';

export function errorHandler(
  error: FastifyError,
  request: FastifyRequest,
  reply: FastifyReply
) {
  request.log.error(error);

  // Zod 验证错误
  if (error instanceof ZodError) {
    return reply.code(400).send({
      code: 400,
      message: '参数验证失败',
      errors: error.errors.map(e => ({
        field: e.path.join('.'),
        message: e.message
      }))
    });
  }

  // 自定义业务错误
  if (error.statusCode) {
    return reply.code(error.statusCode).send({
      code: error.statusCode,
      message: error.message
    });
  }

  // 未知错误
  return reply.code(500).send({
    code: 500,
    message: process.env.NODE_ENV === 'production'
      ? '服务器内部错误'
      : error.message
  });
}
```

```typescript
// src/middleware/auth.ts

import { FastifyRequest, FastifyReply } from 'fastify';

interface JWTPayload {
  userId: string;
  email: string;
}

declare module 'fastify' {
  interface FastifyRequest {
    user: JWTPayload;
  }
}

export async function authenticate(
  request: FastifyRequest,
  reply: FastifyReply
) {
  try {
    const decoded = await request.jwtVerify<JWTPayload>();
    request.user = decoded;
  } catch (err) {
    reply.code(401).send({ code: 401, message: '未授权' });
  }
}
```

### 6. Prisma ORM

```typescript
// src/plugins/prisma.ts

import { FastifyInstance } from 'fastify';
import { PrismaClient } from '@prisma/client';

let prisma: PrismaClient;

export async function prismaPlugin(app: FastifyInstance) {
  prisma = new PrismaClient({
    log: process.env.NODE_ENV === 'development'
      ? ['query', 'error', 'warn']
      : ['error']
  });

  await prisma.$connect();

  app.addHook('onClose', async () => {
    await prisma.$disconnect();
  });

  app.decorate('prisma', prisma);
}

declare module 'fastify' {
  interface FastifyInstance {
    prisma: PrismaClient;
  }
}
```

```typescript
// src/services/user.service.ts

import { FastifyInstance } from 'fastify';
import { prisma } from '../plugins/prisma';

export class UserService {
  async create(data: { username: string; email: string; password: string }) {
    // 检查邮箱唯一性
    const existing = await prisma.user.findUnique({
      where: { email: data.email }
    });

    if (existing) {
      throw Object.assign(new Error('邮箱已存在'), { statusCode: 409 });
    }

    const user = await prisma.user.create({
      data: {
        ...data,
        password: await bcrypt.hash(data.password, 12)
      },
      select: {
        id: true,
        username: true,
        email: true,
        createdAt: true
      }
    });

    return user;
  }

  async findById(id: string) {
    return prisma.user.findUnique({
      where: { id },
      select: {
        id: true,
        username: true,
        email: true,
        createdAt: true
      }
    });
  }
}
```

### 7. Redis 缓存

```typescript
// src/plugins/redis.ts

import Redis from 'ioredis';
import { FastifyInstance } from 'fastify';

let redis: Redis;

export async function redisPlugin(app: FastifyInstance) {
  redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

  redis.on('error', (err) => {
    app.log.error('Redis error:', err);
  });

  app.addHook('onClose', async () => {
    redis.disconnect();
  });

  app.decorate('redis', redis);
}

declare module 'fastify' {
  interface FastifyInstance {
    redis: Redis;
  }
}

// 缓存工具
export const cacheUtils = {
  async getOrSet<T>(
    key: string,
    factory: () => Promise<T>,
    ttlSeconds: number = 300
  ): Promise<T> {
    const cached = await redis.get(key);
    if (cached) {
      return JSON.parse(cached);
    }

    const value = await factory();
    await redis.setex(key, ttlSeconds, JSON.stringify(value));
    return value;
  }
};
```

---

## 触发条件

当用户请求 Node.js 后端开发、Fastify/Express 相关任务、Prisma ORM，或涉及 Node.js 20 / TypeScript 相关问题时，自动应用此技能。
